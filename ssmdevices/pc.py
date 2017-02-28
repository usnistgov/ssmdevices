__all__ = ['ThisPC']

import labbench as lb
import datetime

        
class ThisPC(lb.Device):
    class state(lb.Remotelets):
        time = lb.Bytes(read_only=True)
    
        @time.getter
        def __get_time (self, device):
            now = datetime.datetime.now()
            return '{}.{}'.format(now.strftime('%Y-%m-%d %H:%M:%S'),now.microsecond)
    
    def connect (self):
        pass
    
    def disconnect (self):
        pass
    
    def state_get (self, attr):
        getter = self.state.trait_metadata(attr, 'getter')
        if callable(getter):
            return getter(self)
    
    def state_set (self, *args):
        pass
    
    
if __name__ == '__main__':
    import labbench as lb
    lb.log_to_screen('DEBUG')
    
    with ThisPC() as pc:
        print pc.state.time