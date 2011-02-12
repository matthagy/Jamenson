
import sys

__all__ = '''worst_score best_score no_score
'''.split()

worst_score = sys.maxint
best_score = -sys.maxint
class no_score_type(object):
    def __repr__(self):
        return '<no-score>'
no_score = no_score_type()

# functions that both atypes and coldatypes must implement for multimethods
atypes_multimethods_interface = __all__ + '''
         typep
         as_optimized_type
         type_name
         compose_types_scorer
'''.split()
