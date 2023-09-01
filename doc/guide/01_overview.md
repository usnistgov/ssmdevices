# Overview
The ssmdevices module is organized as a collection of independent device wrappers that are each specialized to specific equipment or software. The wrapper for each hardware model is encapsulated into its own class. Some wrappers, including `IPerf`, are configured to use binaries or calibration data that are bundled with this module.

The wrapper objects here are implemented on [labbench](https://github.com/usnistgov/labbench). A deep understanding of that module is not necessary to use these objects. However, labbench includes many useful tools for organizing the operation of multiple devices. Leveraging those capabilities can help to produce concise code that reads like pseudocode for an experimental procedure.

## Usage strategies
There are two main usage approaches:

* Installation of the module as detailed in [the readme](https://github.com/usnistgov/ssmdevices).

  In this approach, use standard imports to access the desired class, for example:
 
    ```python
    from ssmdevices.software import IPerf3
    ```

* In some cases, it is possible to copy and adjust source code file that defines that class from the
 [`ssmdevices` repository](https://github.com/usnistgov/ssmdevices/tree/main/ssmdevices). In this
 approach, you can then embed the python file with your own code, and import locally.
    - This is typically valid for instruments that are controlled by VISA
    - This does not work easily for instruments that rely on binaries or calibration data that are bundled with ssmdevices

## Contributing
If when you extend a wrapper in your own experiments, please feel free [to open an issue](https://github.com/usnistgov/ssmdevices/issues) to share your code so that we can fold your device back into the code base! 

