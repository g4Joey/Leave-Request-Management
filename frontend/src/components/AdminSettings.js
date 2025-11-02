import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import AdminOverlapSettings from './AdminOverlapSettings';

function AdminSettings() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overlap');

  const canAdmin = user && (user.role === 'admin' || user.is_superuser);
  if (!canAdmin) {
    return (
      <div className="max-w-xl mx-auto bg-white shadow rounded p-6">
        <h3 className="text-lg font-semibold mb-2">Access Denied</h3>
        <p className="text-sm text-gray-600">You do not have permission to view this page.</p>
      </div>
    );
  }

  const tabs = [
    { id: 'overlap', label: 'Overlap Settings', component: AdminOverlapSettings }
    // Future tabs: { id: 'notifications', label: 'Notification Settings', component: AdminNotificationSettings }
    // { id: 'policies', label: 'Leave Policies', component: AdminPolicySettings }
  ];

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg leading-6 font-medium text-gray-900 mb-2">
            Admin Settings
          </h2>
          <p className="text-sm text-gray-600">
            Configure system-wide settings and thresholds.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
        
        {/* Tab Content */}
        <div className="p-6">
          {ActiveComponent && <ActiveComponent />}
        </div>
      </div>
    </div>
  );
}

export default AdminSettings;