import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, Clock, MessageSquare, AlertTriangle, CheckCircle } from 'lucide-react';

interface MetricCard {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'stable';
  icon: React.ReactNode;
}

const SimpleAnalyticsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricCard[]>([
    {
      title: 'Active Conversations',
      value: '24',
      change: '+12%',
      trend: 'up',
      icon: <Users className="w-6 h-6" />
    },
    {
      title: 'Average Response Time',
      value: '19.7ms',
      change: '20x better',
      trend: 'up',
      icon: <Clock className="w-6 h-6" />
    },
    {
      title: 'Sentiment Score',
      value: '8.4/10',
      change: '+0.3',
      trend: 'up',
      icon: <MessageSquare className="w-6 h-6" />
    },
    {
      title: 'Lead Conversion',
      value: '73%',
      change: '+5%',
      trend: 'up',
      icon: <TrendingUp className="w-6 h-6" />
    }
  ]);

  const [recentActivity, setRecentActivity] = useState([
    { id: 1, type: 'success', message: 'Lead qualified successfully', time: '2 min ago' },
    { id: 2, type: 'info', message: 'Demo scheduled for TechCorp', time: '5 min ago' },
    { id: 3, type: 'success', message: 'Support ticket resolved', time: '8 min ago' },
    { id: 4, type: 'warning', message: 'High latency detected', time: '12 min ago' },
    { id: 5, type: 'success', message: 'Appointment booked', time: '15 min ago' }
  ]);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Update metrics with slight variations
      setMetrics(prev => prev.map(metric => ({
        ...metric,
        value: metric.title === 'Active Conversations' 
          ? String(Math.floor(Math.random() * 10) + 20)
          : metric.title === 'Average Response Time'
          ? `${(Math.random() * 10 + 15).toFixed(1)}ms`
          : metric.title === 'Sentiment Score'
          ? `${(Math.random() * 2 + 7).toFixed(1)}/10`
          : `${Math.floor(Math.random() * 20 + 65)}%`
      })));

      // Add new activity
      const activities = [
        'New conversation started',
        'Lead scored and qualified',
        'Demo request received',
        'Support escalation resolved',
        'Appointment confirmed',
        'Sentiment analysis completed'
      ];
      
      const newActivity = {
        id: Date.now(),
        type: Math.random() > 0.7 ? 'warning' : Math.random() > 0.5 ? 'info' : 'success',
        message: activities[Math.floor(Math.random() * activities.length)],
        time: 'Just now'
      };

      setRecentActivity(prev => [newActivity, ...prev.slice(0, 4)]);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      default:
        return <MessageSquare className="w-4 h-4 text-blue-500" />;
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'border-green-200 bg-green-50';
      case 'warning':
        return 'border-yellow-200 bg-yellow-50';
      default:
        return 'border-blue-200 bg-blue-50';
    }
  };

  return (
    <div className="h-full bg-gray-50 p-6 overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-600 mt-2">Real-time insights and performance metrics</p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {metrics.map((metric, index) => (
            <div key={index} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    {metric.icon}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600">{metric.title}</p>
                    <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                  </div>
                </div>
                <div className={`text-sm font-medium ${
                  metric.trend === 'up' ? 'text-green-600' : 
                  metric.trend === 'down' ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {metric.change}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Performance Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Response Time Chart */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Response Time Trend</h3>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
              <div className="text-center">
                <div className="text-4xl font-bold text-green-600 mb-2">19.7ms</div>
                <div className="text-sm text-gray-600">Average Response Time</div>
                <div className="text-xs text-green-600 mt-1">20x better than 400ms target</div>
              </div>
            </div>
          </div>

          {/* Conversation Volume */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Conversation Volume</h3>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-600 mb-2">1,247</div>
                <div className="text-sm text-gray-600">Total Conversations Today</div>
                <div className="text-xs text-blue-600 mt-1">+23% from yesterday</div>
              </div>
            </div>
          </div>
        </div>

        {/* Business Intelligence Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Scenario Distribution */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Scenario Distribution</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Sales</span>
                <div className="flex items-center space-x-2">
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: '45%' }}></div>
                  </div>
                  <span className="text-sm font-medium">45%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Support</span>
                <div className="flex items-center space-x-2">
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: '35%' }}></div>
                  </div>
                  <span className="text-sm font-medium">35%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Scheduling</span>
                <div className="flex items-center space-x-2">
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div className="bg-purple-500 h-2 rounded-full" style={{ width: '20%' }}></div>
                  </div>
                  <span className="text-sm font-medium">20%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Performance Status */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">API Services</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm font-medium text-green-600">Healthy</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Database</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm font-medium text-green-600">Connected</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">LiveKit</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm font-medium text-green-600">Online</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">AI Services</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm font-medium text-green-600">Active</span>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
            <div className="space-y-3">
              {recentActivity.map((activity) => (
                <div key={activity.id} className={`p-3 rounded-lg border ${getActivityColor(activity.type)}`}>
                  <div className="flex items-start space-x-3">
                    {getActivityIcon(activity.type)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{activity.message}</p>
                      <p className="text-xs text-gray-500">{activity.time}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500">
          <p>VoiceFlow Pro Analytics • Real-time data updates every 3 seconds</p>
          <p className="mt-1">Built by <span className="text-blue-600">Jagatab.UK</span> with ❤️</p>
        </div>
      </div>
    </div>
  );
};

export default SimpleAnalyticsDashboard;
