import importlib
import sys
from pathlib import Path

from labbench import Device, Rack, util
from labbench.paramattr import _bases
from labbench.paramattr._bases import (
    ParamAttr,
    Method,
    Undefined,
    Any,
    T,
    get_class_attrs,
    list_value_attrs,
    list_method_attrs,
    list_property_attrs,
)
from labbench.paramattr._bases import _DecoratedMethodCallableType as _TDecoratedMethod
from labbench.paramattr._bases import _KeyedMethodCallableType as _TKeyedMethod
import typing
import astor

util.force_full_traceback(True)

VALID_PARENTS = Device, Rack, ParamAttr

import ast
import typing
from inspect import isclass, signature
from numbers import Number
from ast_decompiler import decompile

from labbench import Device, Rack
import labbench as lb


def nameit(obj):
    if obj is Undefined:
        return "Undefined"
    if isinstance(obj, typing.GenericAlias):
        return repr(obj)
    elif hasattr(obj, "__name__"):
        return obj.__name__
    if hasattr(obj, "__qualname__"):
        return obj.__qualname__

    t = type(obj)
    if hasattr(t, "__name__"):
        return t.__name__
    elif hasattr(t, "__qualname__"):
        return t.__qualname__

    raise TypeError(f"couldn't name {obj}")

def parse_literal(s: str):
    obj = ast.parse(s).body[0].value
    # obj.ctx = context_source
    return obj

def ast_name(name):
    return ast.Name(id=name, kind=None)

def ast_arg(name, annotation=None):
    annotation = ast_name(annotation) if annotation is not None else None
    return ast.arg(arg=name, annotation=annotation, type_comment=None)

def ast_typehint_optional(t, remap={}):
    remap[type(None)] = None
    args = ','.join([getattr(remap.get(sub, sub), '__name__', sub.__class__.__name__) for sub in typing.get_args(t)])
    print('***', f'_typing.Optional[{args}]')
    return parse_literal(f'_typing.Optional[{args}]')

def ast_signature(args, defaults, annotations, posonly_names=[], kwonly_names=[]):
    annotations = {k: nameit(v) for k, v in annotations.items() if v is not Undefined}
    arg_names = [n for n in args if n not in (posonly_names+kwonly_names)]

    return ast.arguments(
        posonlyargs=[ast_arg(a, annotations.get(a, None)) for a in posonly_names],
        kwonlyargs=[ast_arg(a, annotations.get(a, None)) for a in kwonly_names],
        args=[ast_arg(a, annotations.get(a, None)) for a in arg_names],
        vararg=None,
        kwarg=None,  # ast.arg(arg='values', annotation=ast.Name(id='Any', ctx=ast.Load())),
        defaults=[ast_name(repr(d)) for d in defaults[:len(arg_names)+len(posonly_names)] if d is not lb.Undefined],
        kw_defaults=[ast_name(repr(d)) for d in defaults[len(arg_names)+len(posonly_names):] if d is not lb.Undefined],
    )

def ast_function_stub(name, args, defaults, annotations, decorator_list = [], posonly_names=[], kwonly_names=[]):
    if "return" in annotations:
        if isinstance(annotations['return'], (ast.Attribute, ast.Subscript)):
            type_comment = returns = annotations['return']
        else:
            type_comment = returns = ast_name(nameit(annotations["return"]))
    else:
        type_comment = returns = None

    return ast.FunctionDef(
        name=name,
        args=ast_signature(args, defaults, annotations, posonly_names, kwonly_names),
        body=[ast.Expr(value=ast.Constant(value=..., kind=None))],
        decorator_list=decorator_list,
        returns=returns,
        type_comment=type_comment,
    )

def make_method_stubs(cls_def, child_defs, cls: type[lb.Device]):
    print(cls.__qualname__)
    inst = cls()

    for name, attr_def in lb.paramattr.get_class_attrs(cls).items():
        if name == 'bandwidth':
            print('&', name, attr_def, isinstance(attr_def, lb.paramattr.method.Method), name in child_defs)
        if not isinstance(attr_def, lb.paramattr.method.Method):
            continue

        if name not in child_defs:
            continue

        body_index = cls_def.body.index(child_defs[name])
        params = signature(getattr(inst, name)).parameters.values()
        annotations = {p.name: p.annotation for p in params}
        # returns = ast_name(nameit(annotations["return"]))
        # print(annotations)
        # print([
        #         ast.arg(p.name, annotation=nameit(p.annotation))
        #         for p in params
        #         if p.kind is p.KEYWORD_ONLY
        #     ],)

        args = ast.arguments(
            [ast.arg('self')] + [
                ast.arg(p.name, annotation=ast.parse(repr(p.annotation)).body[0])
                for p in params
                if p.kind is p.POSITIONAL_ONLY
            ],

            [
                ast.arg(p.name, annotation=ast.parse(repr(p.annotation)).body[0])
                for p in params
                if p.kind is p.POSITIONAL_OR_KEYWORD
            ],

            None,

            [
                ast.arg(p.name, annotation=ast.parse(getattr(p.annotation, '__qualname__', repr(p.annotation))).body[0])
                for p in params
                if p.kind is p.KEYWORD_ONLY
            ],

            [
                ast_name(p.default)
                for p in params
                if p.kind is p.KEYWORD_ONLY and p.default is not Undefined
            ],

            None,

            [
                ast_name(p.default)
                for p in params
                if p.kind is not p.KEYWORD_ONLY and p.default is not Undefined
            ],
        )

        returns = ast.parse(f'Optional[{attr_def._type.__qualname__}]').body[0]
        cls_def.body[body_index] = ast.FunctionDef(
            name=name,
            args=args,
            body=[ast.Expr(value=ast.Constant(value=..., kind=None))],
            decorator_list=[],
            # returns=returns,
            # type_comment=returns,
        )        

def make_init_stub(cls_def, child_defs, cls: type):
    if '__init__' in child_defs:
        cls_def.body.remove(child_defs['__init__'])

    if issubclass(cls, Device):
        defs = {
            name: getattr(cls,name)
            for name in typing.get_type_hints(cls)
        }

        args = list(defs.keys())
        defaults = {
            attr_def.name: attr_def.default
            for attr_def in defs.values()
            if attr_def.default is not Undefined
        }
        annotations = {
            name: nameit(trait._type)
            for name, trait in defs.items()
        }

    elif issubclass(cls, (ParamAttr, Rack)):
        def transform_annot(cls, a):
            if a is T:
                return cls._type
            else:
                return a
        raw_annots = getattr(cls, "__annotations__", {})
        raw_annots = {k: v for k, v in raw_annots.items() if not k.startswith("_")}

        if issubclass(cls, Method):
            defaults = dict(key=None)
            annotations = dict(key=None)
            args = list(raw_annots.keys())[::-1]
            args.remove('key')
            args = ['key'] + args
        else:
            defaults = {}
            annotations = {}
            args = list(raw_annots.keys())

        defaults.update({name: getattr(cls, name) for name in args})
        defaults = {name: (None if d is Undefined else d) for name, d in defaults.items()}
        annotations.update({
            name: transform_annot(cls, type_)
            for name, type_ in raw_annots.items()
        })
        annotations = {
            name: type_
            for name, type_ in annotations.items()
            if type_ not in (Any, None, Undefined)
        }
    else:
        raise TypeError(f"{cls} is an unknown class type")

    if issubclass(cls, Method) and cls is not Method:
        decorators = [parse_literal('_typing.overload')]

        # for the keyed method determined by setting the 'key' keyword
        annotations['return'] = parse_literal('_bases.TKeyedMethod')
        del defaults['key']
        cls_def.body.insert(0, ast_function_stub('__new__', ['cls'] + args, list(defaults.values()), annotations, decorator_list=decorators))

        # for unkeyed (decorator) method
        annotations['return'] = parse_literal('_bases.TDecoratedMethod')
        annotations.pop('key', None)
        args.remove('key')
        cls_def.body.insert(0, ast_function_stub('__new__', ['cls'] + args, list(defaults.values()), annotations, decorator_list=decorators))
    else:
        cls_def.body.insert(0, ast_function_stub('__init__', ['self'] + args, list(defaults.values()), annotations))

def update_stubs(path, mod_name, sub_name):
    mod = importlib.import_module(f"{mod_name}")
    namespace = importlib.import_module(f"{mod_name}.{sub_name}")

    ast_root = astor.code_to_ast(namespace)
    # with open(path, "r") as f:
    #     ast_root = ast.parse(f.read())

    # identify classes in the root namespace that are one of the desired types
    target_method_name = "__init__"

    # use the interpreter to identify the names of classes with the desired type
    target_names = [
        name
        for name, obj in namespace.__dict__.items()
        if isclass(obj) and issubclass(obj, (ParamAttr, Rack, Device))
    ]

    if len(target_names) > 0:
        print(f"{namespace.__name__}: update {target_names}")
    else:
        return

    # find their definitions in the parsed ast tree
    target_cls_defs = [
        ast_obj
        for ast_obj in ast.iter_child_nodes(ast_root)
        if getattr(ast_obj, "name", None) in target_names
    ]

    def name_node(obj):
        if isinstance(obj, ast.FunctionDef):
            return obj.name
        elif isinstance(obj, ast.Assign):
            return obj.targets[0].id
        elif isinstance(obj, ast.AnnAssign):
            return obj.target.id
        
    for cls_def in target_cls_defs:
        child_defs = {
            name_node(child_def): child_def
            for child_def in ast.iter_child_nodes(cls_def)
        }

        if 'TektronixMSO64B' in cls_def.name:
            print('!!!!!', child_defs.keys(), cls_def.body)
            for item in cls_def.body[:1]:

                print(item.targets[0].id, item.value)

        cls = getattr(namespace, cls_def.name)
        make_init_stub(cls_def, child_defs, cls)
        if issubclass(cls, lb.Device):
            make_method_stubs(cls_def, child_defs, cls)


    with open(path, "w") as f:
        f.write(decompile(ast_root))


if __name__ == "__main__":
    root = Path("ssmdevices")
    mod_name = "ssmdevices"

    # clear out previous files
    for path in root.rglob("*.pyi"):
        Path(path).unlink()

    # stubgen is the first stab
    from mypy import stubgen

    sys.argv = [sys.argv[0], str(root), "-o", str(root / ".."), "-v"]
    stubgen.main()

    # now step through to replace __init__ keyword arguments
    for path in root.rglob("*.pyi"):
        if str(path).endswith("notebook.py"):
            continue

        path = Path(path)

        # convert python path to an importable module name
        sub_name = ".".join(path.with_suffix("").parts[1:])

        update_stubs(path, mod_name=mod_name, sub_name=sub_name)
