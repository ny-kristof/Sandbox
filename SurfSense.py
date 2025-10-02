import SurfSensePanel
import FreeCAD as App

class SurfSense:
    def __init__(self, parent=None):
        self.lower_tolerance = 0.0
        self.upper_tolerance = 0.1
        self.list_of_measurements = []
        self.parent = parent
        self.reflection_ability = None
        self.kinematics = None
        self.sampling_rate = 10
        self.sensor = None
        self.number_of_sensors = 1
    

    def getSensor(self):
        return self.sensor
    

    def setSensor(self, sensor):
        self.sensor = sensor

    
    def getNumberOfSensors(self):
        return self.number_of_sensors
    

    def setNumberOfSensors(self, value):
        self.number_of_sensors = value
    
    
    def getSamplingRate(self):
        return self.sampling_rate
    

    def setSamplingRate(self, value):
        self.sampling_rate = value


    def getKinematics(self):
        return self.kinematics
    

    def setKinematics(self, value):
        self.kinematics = value


    def getReflectionAbility(self):
        return self.reflection_ability
    

    def setReflectionAbility(self, value):
        self.reflection_ability = value


    def setBaseTolerance(self, tolerance_type, value):
        match tolerance_type:
            case "lower":
                self.lower_tolerance = value
                return
            case "upper":
                self.upper_tolerance = value
                return
            case _:
                App.Console.PrintWarning("Unexpected tolerance type")


    def getBaseTolerance(self):
        return (self.lower_tolerance, self.upper_tolerance)
    

    def getMeasurements(self):
        return self.list_of_measurements
    
    
    def addMeasurementToList(self, measurement):
        self.list_of_measurements.append(measurement)


    def removeMeasurement(self, id):
        for m in self.list_of_measurements:
            if m.id == id:
                self.list_of_measurements.remove(m)
                return True
        return False

    
    def getMeasurementByID(self, id):
        for m in self.list_of_measurements:
            if m.id == id:
                return m                
        return None


    def getMeasurementTypes(self):
        m_types = []
        for m in self.list_of_measurements:
            m_types.append(m.measure_type)
        return set(m_types)



class MeasurementData:
    def __init__(self, measure_type, lower_tolerance, upper_tolerance, unit, object_list, measurement, doc_name, sampling_rate, name, object_name, edited_measure_id = None):
        if edited_measure_id is None:
            SurfSensePanel.SurfSensePanel._measurement_count += 1
            self.id = SurfSensePanel.SurfSensePanel._measurement_count
        else:
            self.id = edited_measure_id
        self.measure_type = measure_type
        self.lower_tolerance = lower_tolerance
        self.upper_tolerance = upper_tolerance
        self.unit = unit
        self.object_list = object_list
        self.measurement = measurement
        self.doc_name = doc_name
        self.object_name = object_name
        self.sampling_rate = sampling_rate
        self.name = name


    def setMeasurementName(self, new_name):
        self.name = new_name