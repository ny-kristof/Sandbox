class SurfSense:
    def __init__(self, parent=None):
        self.base_tolerance = 0.5
        self.list_of_measurements = []
        self.parent = parent
        self.reflective_ability = ""

    
    def setBaseTolerance(self, value):
        self.base_tolerance = value


    def getBaseTolerance(self):
        return self.base_tolerance
    

    def getMeasurements(self):
        return self.list_of_measurements
    
    def addMeasurementToList(self, measurement):
        self.list_of_measurements.append(measurement)


class MeasurementData:
    def __init__(self, measure_type, tolerance, unit, object_list, measure):
        self.measure_type = measure_type
        self.tolerance = tolerance
        self.unit = unit
        self.object_list = object_list
        self.measure = measure