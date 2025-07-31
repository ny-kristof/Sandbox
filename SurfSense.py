import SurfSensePanel
import FreeCAD

class SurfSense:
    def __init__(self, parent=None):
        self.base_tolerance = 0.5
        self.list_of_measurements = []
        self.parent = parent
        self.reflection_ability = None
        self.kinematics = None
        self.sampling_rate = 10
        self.sensor = None
        self.number_of_sensors = 0
    

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


    def setBaseTolerance(self, value):
        self.base_tolerance = value


    def getBaseTolerance(self):
        return self.base_tolerance
    

    def getMeasurements(self):
        return self.list_of_measurements
    
    
    def addMeasurementToList(self, measurement):
        self.list_of_measurements.append(measurement)


    def removeMeasurement(self, id):
        for m in self.list_of_measurements:
            if m.id == id:
                self.list_of_measurements.remove(m)
                break

    
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
    def __init__(self, measure_type, tolerance, unit, object_list, measurement, doc_name, sampling_rate, object_name=None):
        SurfSensePanel.SurfSensePanel._measurement_count += 1
        self.id = SurfSensePanel.SurfSensePanel._measurement_count
        self.measure_type = measure_type
        self.tolerance = tolerance
        self.unit = unit
        self.object_list = object_list
        self.measurement = measurement
        self.doc_name = doc_name
        self.object_name = object_name
        self.sampling_rate = sampling_rate
        self.name = f"Measurement-{self.id}: {self.measure_type} | {self.measurement} {self.unit}"


    def setMeasurementName(self, new_name):
        self.name = new_name