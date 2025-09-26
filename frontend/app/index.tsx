import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Alert,
  Platform,
  StatusBar
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface User {
  id: string;
  email: string;
  username: string;
  preferred_languages: string[];
  skill_level: string;
  explanation_language: string;
  total_xp: number;
  streak_days: number;
}

interface DashboardStats {
  user: {
    username: string;
    total_xp: number;
    streak_days: number;
    skill_level: string;
  };
  activity: {
    snippets_created: number;
    questions_solved: number;
    explanations_viewed: number;
  };
  progress: {
    concepts_mastered: number;
    current_level: number;
    next_level_xp: number;
  };
}

export default function CodeLearningPlatform() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentView, setCurrentView] = useState<'login' | 'register' | 'dashboard'>('login');
  const [user, setUser] = useState<User | null>(null);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (token) {
        await fetchUserProfile(token);
        setIsLoggedIn(true);
        setCurrentView('dashboard');
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUserProfile = async (token: string) => {
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        await fetchDashboardStats(token);
      } else {
        throw new Error('Failed to fetch user profile');
      }
    } catch (error) {
      console.error('Fetch user profile failed:', error);
      await AsyncStorage.removeItem('access_token');
      setIsLoggedIn(false);
    }
  };

  const fetchDashboardStats = async (token: string) => {
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/dashboard/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const stats = await response.json();
        setDashboardStats(stats);
      }
    } catch (error) {
      console.error('Fetch dashboard stats failed:', error);
    }
  };

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        await AsyncStorage.setItem('access_token', data.access_token);
        await fetchUserProfile(data.access_token);
        setIsLoggedIn(true);
        setCurrentView('dashboard');
        setEmail('');
        setPassword('');
      } else {
        Alert.alert('Login Failed', data.detail || 'Invalid credentials');
      }
    } catch (error) {
      console.error('Login error:', error);
      Alert.alert('Error', 'Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!email || !password || !username || !confirmPassword) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert('Error', 'Passwords do not match');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          username,
          password,
          preferred_languages: ['python'],
          skill_level: 'beginner',
          explanation_language: 'english',
        }),
      });

      const data = await response.json();

      if (response.ok) {
        await AsyncStorage.setItem('access_token', data.access_token);
        await fetchUserProfile(data.access_token);
        setIsLoggedIn(true);
        setCurrentView('dashboard');
        // Clear form
        setEmail('');
        setPassword('');
        setUsername('');
        setConfirmPassword('');
      } else {
        Alert.alert('Registration Failed', data.detail || 'Registration failed');
      }
    } catch (error) {
      console.error('Registration error:', error);
      Alert.alert('Error', 'Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await AsyncStorage.removeItem('access_token');
      setUser(null);
      setDashboardStats(null);
      setIsLoggedIn(false);
      setCurrentView('login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const renderLoginForm = () => (
    <View style={styles.authContainer}>
      <View style={styles.logoContainer}>
        <Ionicons name="code-slash" size={60} color="#6366f1" />
        <Text style={styles.logoText}>Code Learning Platform</Text>
        <Text style={styles.logoSubtext}>Master programming with AI-powered explanations</Text>
      </View>

      <View style={styles.formContainer}>
        <Text style={styles.formTitle}>Welcome Back</Text>
        
        <TextInput
          style={styles.input}
          placeholder="Email"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          placeholderTextColor="#9ca3af"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholderTextColor="#9ca3af"
        />
        
        <TouchableOpacity
          style={[styles.button, styles.primaryButton]}
          onPress={handleLogin}
          disabled={isLoading}
        >
          <Text style={styles.buttonText}>
            {isLoading ? 'Logging in...' : 'Login'}
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.linkButton}
          onPress={() => setCurrentView('register')}
        >
          <Text style={styles.linkText}>Don't have an account? Sign up</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderRegisterForm = () => (
    <View style={styles.authContainer}>
      <View style={styles.logoContainer}>
        <Ionicons name="code-slash" size={60} color="#6366f1" />
        <Text style={styles.logoText}>Join Us</Text>
        <Text style={styles.logoSubtext}>Start your coding journey today</Text>
      </View>

      <View style={styles.formContainer}>
        <Text style={styles.formTitle}>Create Account</Text>
        
        <TextInput
          style={styles.input}
          placeholder="Username"
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          placeholderTextColor="#9ca3af"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Email"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          placeholderTextColor="#9ca3af"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholderTextColor="#9ca3af"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Confirm Password"
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          secureTextEntry
          placeholderTextColor="#9ca3af"
        />
        
        <TouchableOpacity
          style={[styles.button, styles.primaryButton]}
          onPress={handleRegister}
          disabled={isLoading}
        >
          <Text style={styles.buttonText}>
            {isLoading ? 'Creating Account...' : 'Sign Up'}
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.linkButton}
          onPress={() => setCurrentView('login')}
        >
          <Text style={styles.linkText}>Already have an account? Login</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderDashboard = () => (
    <View style={styles.dashboardContainer}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.welcomeText}>Welcome back!</Text>
          <Text style={styles.usernameText}>{user?.username}</Text>
        </View>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
          <Ionicons name="log-out-outline" size={24} color="#ef4444" />
        </TouchableOpacity>
      </View>

      {/* Stats Cards */}
      <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
        <View style={styles.statsContainer}>
          <View style={styles.statCard}>
            <Ionicons name="flash" size={32} color="#f59e0b" />
            <Text style={styles.statValue}>{dashboardStats?.user.streak_days || 0}</Text>
            <Text style={styles.statLabel}>Day Streak</Text>
          </View>
          
          <View style={styles.statCard}>
            <Ionicons name="trophy" size={32} color="#10b981" />
            <Text style={styles.statValue}>{dashboardStats?.user.total_xp || 0}</Text>
            <Text style={styles.statLabel}>Total XP</Text>
          </View>
          
          <View style={styles.statCard}>
            <Ionicons name="document-text" size={32} color="#6366f1" />
            <Text style={styles.statValue}>{dashboardStats?.activity.snippets_created || 0}</Text>
            <Text style={styles.statLabel}>Code Snippets</Text>
          </View>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          
          <TouchableOpacity style={styles.actionCard}>
            <Ionicons name="code" size={24} color="#6366f1" />
            <View style={styles.actionContent}>
              <Text style={styles.actionTitle}>Code Editor</Text>
              <Text style={styles.actionDescription}>Write code and get AI explanations</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.actionCard}>
            <Ionicons name="help-circle" size={24} color="#10b981" />
            <View style={styles.actionContent}>
              <Text style={styles.actionTitle}>Practice Questions</Text>
              <Text style={styles.actionDescription}>Test your knowledge</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.actionCard}>
            <Ionicons name="stats-chart" size={24} color="#f59e0b" />
            <View style={styles.actionContent}>
              <Text style={styles.actionTitle}>Progress Tracking</Text>
              <Text style={styles.actionDescription}>View your learning journey</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
          </TouchableOpacity>
        </View>

        {/* Skill Level */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Your Profile</Text>
          <View style={styles.profileCard}>
            <Text style={styles.profileLabel}>Skill Level</Text>
            <Text style={styles.profileValue}>{user?.skill_level}</Text>
            
            <Text style={styles.profileLabel}>Preferred Languages</Text>
            <Text style={styles.profileValue}>
              {user?.preferred_languages?.join(', ') || 'Python'}
            </Text>
            
            <Text style={styles.profileLabel}>Explanation Language</Text>
            <Text style={styles.profileValue}>{user?.explanation_language}</Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );

  if (isLoading) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <Ionicons name="code-slash" size={60} color="#6366f1" />
        <Text style={styles.loadingText}>Loading...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
      {currentView === 'login' && renderLoginForm()}
      {currentView === 'register' && renderRegisterForm()}
      {currentView === 'dashboard' && renderDashboard()}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#ffffff',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#6366f1',
    fontWeight: '500',
  },
  authContainer: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 48,
  },
  logoText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1f2937',
    marginTop: 16,
  },
  logoSubtext: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    marginTop: 8,
  },
  formContainer: {
    width: '100%',
  },
  formTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 24,
    textAlign: 'center',
  },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
    backgroundColor: '#f9fafb',
    color: '#1f2937',
  },
  button: {
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  primaryButton: {
    backgroundColor: '#6366f1',
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  linkButton: {
    alignItems: 'center',
  },
  linkText: {
    color: '#6366f1',
    fontSize: 14,
  },
  dashboardContainer: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  welcomeText: {
    fontSize: 14,
    color: '#6b7280',
  },
  usernameText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1f2937',
    marginTop: 4,
  },
  logoutButton: {
    padding: 8,
  },
  scrollContainer: {
    flex: 1,
    padding: 24,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 32,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 16,
    alignItems: 'center',
    marginHorizontal: 4,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 16,
  },
  actionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 16,
    marginBottom: 12,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  actionContent: {
    flex: 1,
    marginLeft: 16,
  },
  actionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
  },
  actionDescription: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
  },
  profileCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  profileLabel: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 12,
    marginBottom: 4,
  },
  profileValue: {
    fontSize: 16,
    color: '#1f2937',
    fontWeight: '500',
    textTransform: 'capitalize',
  },
});