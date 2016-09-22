from qgis.core import *
import pickle
import networkx as nx

# QGIS Processing Script Parameters "##" indicates a parameter to QGIS
##[Graph]=group
##Vector=vector
##Field=field Vector
##Output_File_Path=file


def rectBounds(geometry):
    """
    Generates bounding rectangles for QGIS polygon geometries.

    :param geometry: A QGIS feature geometry
    :type geometry: QgsGeometry
    :return: A list of the lower left and upper right coordinates of
        a bounding rectangle for the input geometry
    :rtype: list
    :return list entry type: float
    """
    coordList = geometry.asPolygon()
    x = []
    y = []
    for i in range(len(coordList)):
        x.append(coordList[0][i].x())
        y.append(coordList[0][i].y())
    return [min(x), min(y), max(x), max(y)]


def filter(layer, exp):
    """
    Filters the features of a vector layer by an expression.

    :param layer: A QGIS vector layer
    :type layer: QgsVectorLayer
    :param exp: A QGIS expression
    :type exp: QgsExpression
    :raises Exception: Parser Error
    :raises ValueError:
    :yield: features
    :ytype: QgsFeature
    """
    if exp.hasParserError():
        raise Exception(exp.parserErrorString())
    exp.prepare(layer.pendingFields())
    for feature in layer.getFeatures():
        value = exp.evaluate(feature)
        if exp.hasEvalError():
            raise ValueError(exp.evalErrorString())
        if bool(value):
            yield feature


def quickFilter(layer, exp):
    """
    Returns the first feature found satisfying the expression.

    This function is a copy of filter with a 'return' statement
    in place of the 'yield' statement

    :param layer: A QGIS vector layer
    :type layer: QgsVectorLayer
    :param exp: A QGIS expression
    :type exp: QgsExpression
    :raises Exception: Parser Error
    :raises ValueError:
    :return: feature
    :rtype: QgsFeature
    """
    if exp.hasParserError():
        raise Exception(exp.parserErrorString())
    exp.prepare(layer.pendingFields())
    for feature in layer.getFeatures():
        value = exp.evaluate(feature)
        if exp.hasEvalError():
            raise ValueError(exp.evalErrorString())
        if bool(value):
            return feature


def buildExpression(field, value):
    """
    Constructs an expression of the form field = value.

    :param field: A vector layer attribute field name
    :type field: str
    :param value: A value for the attribute field taken on by features
                  in the layer
    :return: Expression
    :rtype: QgsExpression
    """
    try:
        float(value)
        exp = field + "=" + value
    except:
        exp = field + "=\'" + value + "\'"
    return QgsExpression(exp)


def updateEdges(dictionary, fieldValue1, fieldValue2):
    """
    Updates both vertices' 'edges' lists in the dictonary.

    :param dictionary: The graphDictionary to be updated
    :type dictionary: dict
    :param fieldValue*: An attribute field value
    :type fieldValue*: str
    :return: the updated dictionary
    :rtype: dict
    """
    dictionary[fieldValue1]['edges'].append(fieldValue2)
    dictionary[fieldValue2]['edges'].append(fieldValue1)
    return dictionary


def findEdges(valueSet, boundsIndexDict, graphDict, features):
    """
    Generates the edge lists for the graphDictionary

    This function does most of the heavy lifting. The nested for loops
    are written such that after each iteration of the outer loop, the
    inner loop shrinks. It also takes advantage of the bounding
    rectangles and spatial indices, in order to optimize its runtime.

    :param valueSet: the values taken on by the input attribute field
    :type valueSet: set
    :param boundsIndexDict: the boundsAndIndexDict {vertex:[bounds,idx]}
    :type boundsIndexDict: dict
    :param graphDict: the current graph data {vertex:dict}
    :type graphDict: dict
    :param features: the dictionary {feature.id():feature}
    :type features: dict
    :return: the updated graphDict
    :rtype: dict
    """
    valueSet2 = valueSet.copy()

    for value1 in valueSet:
        valueSet2.remove(value1)
        index1 = boundsIndexDict[value1][1]
        bounds = boundsIndexDict[value1][0]
        rectangle1 = QgsRectangle(bounds[0], bounds[1], bounds[2], bounds[3])

        for value2 in valueSet:
            index2 = boundsIndexDict[value2][1]
            tempBounds = boundsIndexDict[value2][0]
            rectangle2 = QgsRectangle(tempBounds[0], tempBounds[1], tempBounds[2], tempBounds[3])

            if rectangle1.intersects(rectangle2):
                rectangle3 = smallRectangle(bounds, tempBounds)
                ids1 = index1.intersects(rectangle3)
                ids2 = index2.intersects(rectangle3)
                finish = False

                while (finish is False):
                    for id1 in ids1:
                        feature1 = features[id1]

                        for id2 in ids2:
                            feature2 = features[id2]
                            
                            if feature2.geometry().intersects(feature1.geometry()):
                                graphDict = updateEdges(graphDict, value1, value2)
                                finish = True
                    finish = True
    return graphDict


def processParameters(vector, field):
    """
    Does the initial processing of the parameters.
    
    :param vector: the vector layer to process
    :type vector: unicode
    :param field: the field which defines the graph vertices
    :type field: str
    :return: the inputs processed into dictionaries, sets, lists, and a 
             QgsVectorLayer
    :rtype: list
    """
    
    allFeatures = {}
    layerFields = []
    graphDictionary = {}
    fieldValues = set()
    inputLayer = processing.getObject(vector)
    for feature in inputLayer.getFeatures():
        fieldValues.add(str(feature[Field]))
        allFeatures[feature.id()] = feature

    for field in inputLayer.pendingFields():
        layerFields.append(str(field.name()))

    for value in fieldValues:
        graphDictionary[value] = {}
        graphDictionary[value]['edges'] = []
        
    return [allFeatures, fieldValues, graphDictionary, layerFields, inputLayer]


def boundsAndIndexDict(layer, valueSet, field):
    """
    Generates the dictionary {vertex : [bounds, spatialIndex]}
    
    The dictionary generated by this function is used to optimize the
    findEdges() function.

    :param layer: A QGIS vector layer
    :type layer: QgsVectorLayer
    :param valueSet: the set of values taken on by the attribute field
    :type valueSet: set
    :type valueSet elements: str
    :param field: the attribute field
    :param type: str
    :return: the dictionary {vertex : [bounds, spatialIndex]}
    :rtype: dict
    :rvalues: A list whose first entry is a list and whose second entry
              is a QgsSpatialIndex
    """

    boundsIndexDict = {}
    for value in valueSet:
        spatialIndex = QgsSpatialIndex()
        expression = buildExpression(field, value)
        x = []
        y = []

        for feature in filter(layer, expression):
            geom = feature.geometry()
            spatialIndex.insertFeature(feature)
            featureBounds = rectBounds(geom)
            x.extend([featureBounds[0], featureBounds[2]])
            y.extend([featureBounds[1], featureBounds[3]])

        boundsIndexDict[value] = [[min(x), min(y), max(x), max(y)], spatialIndex]

    return boundsIndexDict


def addAttributesDict(layer, vertexField, layerFields, graphDictionary):
    """
    Adds an attributes dictionary to the graph dictionary for each vertex.

    The attributes dictionary has the form {field: fieldValue} for 
    every field in the attributes table of the vector layer. The
    fieldValues come from the feature returned by quickFilter.
    
    :param layer: A QGIS vector Layer
    :type layer: QgsVectorLayer
    :param vertexField: A vector layer attributes field
    :type vertexField: str
    :param layerFields: a list of the vector layer attribute fields
    :type layerFields: list
    :param graphDictionary: The dictionary {vertex : dict}
    :type graphDictionary: dict
    :return: graphDictionary updated with an attributes dictionary for
             every vertex
    :rtype: dict
    """
    for key in graphDictionary:
        expression = buildExpression(vertexField, key)
        featureInstance = quickFilter(layer, expression)
        attributesDictionary = {}
        for field in layerFields:
            try:
                attributesDictionary[field] = float(featureInstance[field])
            except:
                attributesDictionary[field] = str(featureInstance[field])
        graphDictionary[key]['attributes'] = attributesDictionary
    return graphDictionary


def smallRectangle(bounds1, bounds2):
    """
    Generates the rectangle bounded by the intersection of the parameters

    :param bounds*: A list of bounds, [xMin, yMin, xMax, yMax]
    :type bounds*: list
    :type bounds* elements: float
    :return: A QGIS Rectangle
    :rtype: QgsRectangle
    """
    xMin = max(bounds1[0], bounds2[0])
    yMin = max(bounds1[1], bounds2[1])
    xMax = min(bounds1[2], bounds2[2])
    yMax = min(bounds1[3], bounds2[3])
    return QgsRectangle(xMin, yMin, xMax, yMax)


def buildGraph(vector, field):
    """
    Builds the graph as a dictionary

    The dictionary has the following form:
    {vertex: {'edges': [vertices adjacent to the vertex],
    'attributes': {field : fieldValue} (for every field in the
    attributes table of the vector layer)}
    
    :param vector: the QGIS parameter Vector
    :type vector: unicode
    :param field: the QGIS parameter Field
    :type field: str
    :return: The graph
    :rtype: dict
    """
    parameters = processParameters(vector, field)
    allFeatures = parameters[0]
    fieldValues = parameters[1]
    graphDict = parameters[2]
    layerFields = parameters[3]
    layer = parameters[4]
    bdsIdxDict = boundsAndIndexDict(layer, fieldValues, field)
    graphDict = findEdges(fieldValues, bdsIdxDict, graphDict, allFeatures)
    graphDict = addAttributesDict(layer, field, layerFields, graphDict)
    return graphDict


def nxGraph(graphDict):
    """
    Transforms a graphDict into a NetworkX graph object

    :param graphDict: Graph data stored as a dictionary
    :type graphDict: dict
    :return: Graph
    :rtype: nx.Graph() object
    """

    graph = nx.Graph()
    for vertex, data in graphDict.iteritems():
        graph.add_node(vertex)
        edgeList = nxEdgeTuples(vertex, data['edges'])
        graph.add_edges_from(edgeList)
        graph.node[vertex]['attributes'] = data['attributes']

    return graph


def nxEdgeTuples(vertex, edgeList):
    """
    Generates the list [(vertex, neighbor1), (vertex, neighbor2),...]
    
    :param vertex: A vertex in the graph
    :type vertex: str
    :param edgeList: A list of the vertex's neighbors
    :type edgeList: list
    :return: a list of edges as tuples
    :rtype: list 
    """
    edgeTuples = []
    for edge in edgeList:
        edgeTuples.append((vertex, edge))
    return edgeTuples


def pickleDump(path, data):
    with open(path, 'wb') as f:
        pickle.dump(data, f)


def runInputs(vector, field, path):
    graph = buildGraph(vector, field)
    graph = nxGraph(graph)
    pickleDump(path, graph)


runInputs(Vector, Field, Output_File_Path) # runs the script
