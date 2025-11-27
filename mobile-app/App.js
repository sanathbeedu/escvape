import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Image,
  Alert,
  ScrollView,
  TextInput,
  Switch,
  ActivityIndicator,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';

const Tab = createBottomTabNavigator();

// API Configuration
const API_BASE_URL = 'http://192.168.1.100:8000'; // Update with your server IP

// Detection Screen Component
function DetectionScreen() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 1,
    });

    if (!result.canceled) {
      setSelectedImage(result.assets[0]);
      setResults(null);
    }
  };

  const takePhoto = async () => {
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 1,
    });

    if (!result.canceled) {
      setSelectedImage(result.assets[0]);
      setResults(null);
    }
  };

  const analyzeImage = async () => {
    if (!selectedImage) {
      Alert.alert('Error', 'Please select an image first');
      return;
    }

    setIsAnalyzing(true);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append('file', {
        uri: selectedImage.uri,
        type: 'image/jpeg',
        name: 'image.jpg',
      });
      formData.append('confidence_threshold', confidenceThreshold.toString());

      const response = await fetch(`${API_BASE_URL}/detect/single`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.ok) {
        const result = await response.json();
        setResults(result);
      } else {
        Alert.alert('Error', 'Failed to analyze image');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error: ' + error.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>🚭 Cigarette Detection</Text>
      
      {/* Image Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Select Image</Text>
        <View style={styles.buttonRow}>
          <TouchableOpacity style={styles.button} onPress={pickImage}>
            <Text style={styles.buttonText}>📁 Gallery</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.button} onPress={takePhoto}>
            <Text style={styles.buttonText}>📷 Camera</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Selected Image */}
      {selectedImage && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Selected Image</Text>
          <Image source={{ uri: selectedImage.uri }} style={styles.selectedImage} />
        </View>
      )}

      {/* Confidence Threshold */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Confidence Threshold: {confidenceThreshold.toFixed(2)}</Text>
        <View style={styles.sliderContainer}>
          <Text>0.1</Text>
          <View style={styles.slider}>
            <TouchableOpacity
              style={[styles.sliderThumb, { left: `${(confidenceThreshold - 0.1) / 0.9 * 100}%` }]}
              onPressIn={() => {}}
            />
          </View>
          <Text>1.0</Text>
        </View>
      </View>

      {/* Analyze Button */}
      <TouchableOpacity 
        style={[styles.analyzeButton, isAnalyzing && styles.buttonDisabled]} 
        onPress={analyzeImage}
        disabled={isAnalyzing}
      >
        {isAnalyzing ? (
          <ActivityIndicator color="white" />
        ) : (
          <Text style={styles.analyzeButtonText}>🔍 Analyze Image</Text>
        )}
      </TouchableOpacity>

      {/* Results */}
      {results && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Results</Text>
          <View style={styles.resultsContainer}>
            <View style={[styles.resultCard, results.cigarette_detected ? styles.alertCard : styles.safeCard]}>
              <Text style={styles.resultTitle}>
                {results.cigarette_detected ? '🚨 CIGARETTE DETECTED!' : '✅ No Cigarette Detected'}
              </Text>
              {results.cigarette_detected && (
                <Text style={styles.confidenceText}>
                  Max Confidence: {(results.max_confidence * 100).toFixed(1)}%
                </Text>
              )}
            </View>
            
            {results.detections && results.detections.length > 0 && (
              <View style={styles.detectionsContainer}>
                <Text style={styles.detectionsTitle}>Detailed Detections:</Text>
                {results.detections.map((detection, index) => (
                  <View key={index} style={styles.detectionItem}>
                    <Text style={styles.detectionText}>
                      {detection.class} ({(detection.confidence * 100).toFixed(1)}%)
                      {detection.is_cigarette_related && ' [CIGARETTE-RELATED]'}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

// Parental Control Screen Component
function ParentalControlScreen() {
  const [parentEmail, setParentEmail] = useState('');
  const [deviceId, setDeviceId] = useState('mobile_device_001');
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [settings, setSettings] = useState({
    realTimeAlerts: true,
    dailyReports: true,
    sensitivityLevel: 'medium',
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const savedEmail = await AsyncStorage.getItem('parentEmail');
      const savedDeviceId = await AsyncStorage.getItem('deviceId');
      const savedSettings = await AsyncStorage.getItem('monitoringSettings');
      
      if (savedEmail) setParentEmail(savedEmail);
      if (savedDeviceId) setDeviceId(savedDeviceId);
      if (savedSettings) setSettings(JSON.parse(savedSettings));
    } catch (error) {
      console.log('Error loading settings:', error);
    }
  };

  const saveSettings = async () => {
    try {
      await AsyncStorage.setItem('parentEmail', parentEmail);
      await AsyncStorage.setItem('deviceId', deviceId);
      await AsyncStorage.setItem('monitoringSettings', JSON.stringify(settings));
    } catch (error) {
      console.log('Error saving settings:', error);
    }
  };

  const startMonitoring = async () => {
    try {
      const trimmedDeviceId = deviceId.trim();
      const trimmedEmail = parentEmail.trim();

      if (!trimmedDeviceId) {
        Alert.alert('Error', 'Please enter device ID');
        return;
      }

      const body = {
        deviceId: trimmedDeviceId,
        settings: {
          ...settings,
          monitoredApps: ['youtube', 'tiktok', 'instagram', 'netflix'],
        },
      };

      // Include parentEmail only if provided (optional for starting monitoring)
      if (trimmedEmail) {
        body.parentEmail = trimmedEmail;
      }

      const response = await fetch(`${API_BASE_URL}/parental-control/start-monitoring`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (response.ok) {
        setIsMonitoring(true);
        await saveSettings();
        Alert.alert('Success', 'Video monitoring started successfully!');
      } else {
        Alert.alert('Error', 'Failed to start monitoring');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error: ' + error.message);
    }
  };

  const stopMonitoring = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/parental-control/stop-monitoring?device_id=${deviceId}`, {
        method: 'POST',
      });

      if (response.ok) {
        setIsMonitoring(false);
        Alert.alert('Success', 'Video monitoring stopped');
      } else {
        Alert.alert('Error', 'Failed to stop monitoring');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error: ' + error.message);
    }
  };

  const sendTestReport = async () => {
    if (!parentEmail.trim()) {
      Alert.alert('Error', 'Please enter parent email');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/parental-control/send-test-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          parentEmail: parentEmail.trim(),
        }),
      });

      if (response.ok) {
        Alert.alert('Success', 'Test report sent successfully!');
      } else {
        Alert.alert('Error', 'Failed to send test report');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error: ' + error.message);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>👨‍👩‍👧‍👦 Parental Control</Text>

      {/* Configuration */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Configuration</Text>
        
        <View style={styles.inputContainer}>
          <Text style={styles.inputLabel}>Parent Email:</Text>
          <TextInput
            style={styles.textInput}
            value={parentEmail}
            onChangeText={setParentEmail}
            placeholder="parent@example.com"
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.inputLabel}>Device ID:</Text>
          <TextInput
            style={styles.textInput}
            value={deviceId}
            onChangeText={setDeviceId}
            placeholder="mobile_device_001"
          />
        </View>
      </View>

      {/* Monitoring Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Monitoring Settings</Text>
        
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Real-time Alerts</Text>
          <Switch
            value={settings.realTimeAlerts}
            onValueChange={(value) => setSettings({...settings, realTimeAlerts: value})}
          />
        </View>

        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Daily Reports</Text>
          <Switch
            value={settings.dailyReports}
            onValueChange={(value) => setSettings({...settings, dailyReports: value})}
          />
        </View>

        <View style={styles.inputContainer}>
          <Text style={styles.inputLabel}>Sensitivity Level:</Text>
          <View style={styles.pickerContainer}>
            {['low', 'medium', 'high'].map((level) => (
              <TouchableOpacity
                key={level}
                style={[
                  styles.pickerOption,
                  settings.sensitivityLevel === level && styles.pickerOptionSelected
                ]}
                onPress={() => setSettings({...settings, sensitivityLevel: level})}
              >
                <Text style={[
                  styles.pickerOptionText,
                  settings.sensitivityLevel === level && styles.pickerOptionTextSelected
                ]}>
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </View>

      {/* Monitoring Control */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Monitoring Control</Text>
        
        <View style={styles.statusContainer}>
          <Text style={styles.statusLabel}>Status:</Text>
          <Text style={[styles.statusText, isMonitoring ? styles.statusActive : styles.statusInactive]}>
            {isMonitoring ? 'Active' : 'Inactive'}
          </Text>
        </View>

        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.button, styles.startButton, isMonitoring && styles.buttonDisabled]}
            onPress={startMonitoring}
            disabled={isMonitoring}
          >
            <Text style={styles.buttonText}>▶️ Start Monitoring</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.stopButton, !isMonitoring && styles.buttonDisabled]}
            onPress={stopMonitoring}
            disabled={!isMonitoring}
          >
            <Text style={styles.buttonText}>⏹️ Stop Monitoring</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.testButton} onPress={sendTestReport}>
          <Text style={styles.buttonText}>📧 Send Test Report</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

// Statistics Screen Component
function StatsScreen() {
  const [stats, setStats] = useState({
    totalVideosWatched: 0,
    smokingContentDetected: 0,
    lastDetection: null,
    dailyStats: [],
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    refreshStats();
    const interval = setInterval(refreshStats, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const refreshStats = async () => {
    setIsLoading(true);
    try {
      const deviceId = await AsyncStorage.getItem('deviceId') || 'mobile_device_001';
      const response = await fetch(`${API_BASE_URL}/parental-control/stats?device_id=${deviceId}`);
      
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.log('Error fetching stats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const detectionRate = stats.totalVideosWatched > 0 
    ? (stats.smokingContentDetected / stats.totalVideosWatched * 100).toFixed(1)
    : '0.0';

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>📊 Monitoring Statistics</Text>

      {isLoading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Loading statistics...</Text>
        </View>
      )}

      {/* Current Statistics */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Current Statistics</Text>
        
        <View style={styles.statsGrid}>
          <View style={styles.statCard}>
            <Text style={styles.statNumber}>{stats.totalVideosWatched}</Text>
            <Text style={styles.statLabel}>Videos Watched</Text>
          </View>

          <View style={styles.statCard}>
            <Text style={[styles.statNumber, styles.alertNumber]}>{stats.smokingContentDetected}</Text>
            <Text style={styles.statLabel}>Smoking Content</Text>
          </View>

          <View style={styles.statCard}>
            <Text style={styles.statNumber}>{detectionRate}%</Text>
            <Text style={styles.statLabel}>Detection Rate</Text>
          </View>

          <View style={styles.statCard}>
            <Text style={styles.statNumber}>
              {stats.lastDetection ? new Date(stats.lastDetection).toLocaleDateString() : 'Never'}
            </Text>
            <Text style={styles.statLabel}>Last Detection</Text>
          </View>
        </View>
      </View>

      {/* Daily Statistics */}
      {stats.dailyStats && stats.dailyStats.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Daily Statistics</Text>
          {stats.dailyStats.map((day, index) => (
            <View key={index} style={styles.dailyStatRow}>
              <Text style={styles.dailyStatDate}>{day.date}</Text>
              <Text style={styles.dailyStatText}>Videos: {day.videos}</Text>
              <Text style={styles.dailyStatText}>Detections: {day.detections}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Refresh Button */}
      <TouchableOpacity style={styles.refreshButton} onPress={refreshStats}>
        <Text style={styles.buttonText}>🔄 Refresh Statistics</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// Main App Component
export default function App() {
  useEffect(() => {
    // Request permissions
    (async () => {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission needed', 'Camera roll permissions are required to select images.');
      }
    })();
  }, []);

  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          tabBarActiveTintColor: '#007AFF',
          tabBarInactiveTintColor: 'gray',
          headerShown: false,
        }}
      >
        <Tab.Screen
          name="Detection"
          component={DetectionScreen}
          options={{
            tabBarLabel: 'Detection',
            tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>🔍</Text>,
          }}
        />
        <Tab.Screen
          name="ParentalControl"
          component={ParentalControlScreen}
          options={{
            tabBarLabel: 'Parental Control',
            tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>👨‍👩‍👧‍👦</Text>,
          }}
        />
        <Tab.Screen
          name="Stats"
          component={StatsScreen}
          options={{
            tabBarLabel: 'Stats',
            tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>📊</Text>,
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
    color: '#333',
  },
  section: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 15,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 12,
    borderRadius: 8,
    flex: 0.48,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  selectedImage: {
    width: '100%',
    height: 200,
    borderRadius: 8,
    resizeMode: 'contain',
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  slider: {
    flex: 1,
    height: 20,
    backgroundColor: '#ddd',
    borderRadius: 10,
    marginHorizontal: 10,
    position: 'relative',
  },
  sliderThumb: {
    width: 20,
    height: 20,
    backgroundColor: '#007AFF',
    borderRadius: 10,
    position: 'absolute',
    top: 0,
  },
  analyzeButton: {
    backgroundColor: '#34C759',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 15,
  },
  analyzeButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  resultsContainer: {
    marginTop: 10,
  },
  resultCard: {
    padding: 15,
    borderRadius: 8,
    marginBottom: 10,
  },
  alertCard: {
    backgroundColor: '#FFE5E5',
    borderColor: '#FF3B30',
    borderWidth: 2,
  },
  safeCard: {
    backgroundColor: '#E5F5E5',
    borderColor: '#34C759',
    borderWidth: 2,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  confidenceText: {
    fontSize: 14,
    textAlign: 'center',
    marginTop: 5,
    color: '#666',
  },
  detectionsContainer: {
    marginTop: 10,
  },
  detectionsTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  detectionItem: {
    backgroundColor: '#f8f8f8',
    padding: 8,
    borderRadius: 5,
    marginBottom: 3,
  },
  detectionText: {
    fontSize: 12,
    color: '#666',
  },
  inputContainer: {
    marginBottom: 15,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 5,
    color: '#333',
  },
  textInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 10,
    fontSize: 16,
    backgroundColor: 'white',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  settingLabel: {
    fontSize: 16,
    color: '#333',
  },
  pickerContainer: {
    flexDirection: 'row',
    marginTop: 5,
  },
  pickerOption: {
    flex: 1,
    padding: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 5,
    marginHorizontal: 2,
    alignItems: 'center',
  },
  pickerOptionSelected: {
    backgroundColor: '#007AFF',
  },
  pickerOptionText: {
    color: '#333',
  },
  pickerOptionTextSelected: {
    color: 'white',
    fontWeight: 'bold',
  },
  statusContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  statusLabel: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  statusText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  statusActive: {
    color: '#34C759',
  },
  statusInactive: {
    color: '#FF3B30',
  },
  startButton: {
    backgroundColor: '#34C759',
  },
  stopButton: {
    backgroundColor: '#FF3B30',
  },
  testButton: {
    backgroundColor: '#FF9500',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  loadingContainer: {
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: '#f8f8f8',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 10,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  alertNumber: {
    color: '#FF3B30',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginTop: 5,
  },
  dailyStatRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 10,
    backgroundColor: '#f8f8f8',
    borderRadius: 5,
    marginBottom: 5,
  },
  dailyStatDate: {
    fontWeight: 'bold',
    color: '#333',
  },
  dailyStatText: {
    color: '#666',
  },
  refreshButton: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 20,
  },
});
