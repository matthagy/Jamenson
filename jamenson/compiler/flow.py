'''Flow graphs of program executions.
   (Will someday be) Used for more extensive analysis of IR.
'''

from . import ir as I
from .bind import BindingUse

class FlowObj(object):

    pass


class FlowBinding(FlowObj):

    def __init__(self, binding):
        assert isinstance(binding, BindingUse)
        self.binding = binding

class Read(FlowBinding):

    pass

class Write(FlowBinding):

    pass

class Delete(FlowBinding):

    pass

class Branch(FlowObj):

    def __init__(self, condition, then, else_):
        assert isinstance(condition, FlowObj)
        assert isinstance(then, FlowObj)
        assert isinstance(else_, FlowObj)
        self.condition = condition
        self.then = then
        self.else_ = else_

class Seq(FlowObj):

    def __init__(self, flows):
        flows = list(flows)
        assert all(isinstance(flow, FlowObj) for flow in flows)
        self.flows = flows

class Call(FlowObj):

    def __init__(self, callee, compounded_arguments):
        assert isinstance(callee, FlowObj)
        assert isinstance(compounded_arguments, FlowObj)
        self.callee = callee
        self.compounded_arguments = compounded_arguments

class Return(FlowObj):

    def __init__(self, value):
        assert isinstance(value, FlowObj)
        self.value = value

