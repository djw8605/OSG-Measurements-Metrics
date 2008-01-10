
from graphtool.graphs.graph import DBGraph, TimeGraph, \
    SummarizePivotGroupGraph, SummarizePivotGraph
from graphtool.graphs.common_graphs import StackedBarGraph, BarGraph, \
    CumulativeGraph, PieGraph, QualityMap
import types

from graphtool.graphs.graph import prefs

prefs['watermark'] = '$CONFIG_ROOT/osg_logo_4c_white.png'

class GratiaStackedBar(SummarizePivotGroupGraph, TimeGraph, StackedBarGraph):
  pass

class GratiaBar( TimeGraph, StackedBarGraph ):
  pass

class GratiaCumulative(SummarizePivotGroupGraph, CumulativeGraph):
  pass

class GratiaPie( SummarizePivotGraph, TimeGraph, PieGraph ):
  pass

