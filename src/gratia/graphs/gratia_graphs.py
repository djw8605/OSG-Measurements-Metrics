
from graphtool.graphs.graph import DBGraph, TimeGraph, \
    SummarizePivotGroupGraph, SummarizePivotGraph
from graphtool.graphs.common_graphs import StackedBarGraph, BarGraph, \
    CumulativeGraph, PieGraph, QualityMap, StackedLineGraph
import types

from graphtool.graphs.graph import prefs

#prefs['watermark'] = '$CONFIG_ROOT/osg_logo_4c_white.png'
prefs['watermark'] = 'False'

class GratiaColors:

    pass
    #hex_colors = [ "#ff3333", "#ffff99", "#66ff00", "#9966ff", "#ff9900", "#996633",
    #               "#666699", "#33ccff", "#99cccc", "#ff33ff", "#990099", "#ffcc99",
    #               "#3366ff", "#33cccc" ]



class GratiaStackedBar(GratiaColors, SummarizePivotGroupGraph, TimeGraph, StackedBarGraph):
  pass

class GratiaBar(GratiaColors, TimeGraph, BarGraph):
  pass

class GratiaCumulative(GratiaColors, SummarizePivotGroupGraph, CumulativeGraph):
  pass

class GratiaPie(GratiaColors, SummarizePivotGraph, TimeGraph, PieGraph ):
  pass

class GratiaStackedLine(GratiaColors, SummarizePivotGroupGraph, TimeGraph, StackedLineGraph):
  pass

