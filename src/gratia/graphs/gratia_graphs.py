
from graphtool.graphs.graph import DBGraph, TimeGraph
from graphtool.graphs.common_graphs import StackedBarGraph, BarGraph, CumulativeGraph, PieGraph, QualityMap
import types

class GratiaStackedBar( TimeGraph, StackedBarGraph ):
  pass

class GratiaBar( TimeGraph, StackedBarGraph ):
  pass

class GratiaCumulative( CumulativeGraph ):
  pass

class GratiaPie( TimeGraph, PieGraph ):
  pass

