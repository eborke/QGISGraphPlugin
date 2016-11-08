# QGIS Polygons to Graph

This sub-plugin of processing generates a graph data structure from a vector file of polygons according to an attribute field chosen by the user. The graph contains one vertex for every distinct value of the chosen attribute field. Two vertices share an edge if any of their corresponding polygons intersect. The graph object is pickled and saved to a user chosen location, so that they may then write their own scripts for analysis.

## Prerequisites

* [QGIS](www.qgis.org)
* [Python](www.python.org)
* [NetworkX](https://networkx.github.io/)

## Installing
Inside of QGIS open up the processing toolbox, and run "Add script from file" and choose the file "Graph.py". The script will then be accessible in the processing toolbox and found here: 

```
Scripts -> Graph -> Graph
```
## Author

* **Erik Borke**

## License

This project is licensed under the GPL version 3 - see the LICENSE.md file for details
