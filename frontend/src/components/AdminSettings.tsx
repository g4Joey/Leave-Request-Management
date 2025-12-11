import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import AdminOverlapSettings from './AdminOverlapSettings';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings, Shield, Bell } from 'lucide-react';

function AdminSettings() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overlap');

  const canAdmin = user && (user.role === 'admin' || user.is_superuser);
  if (!canAdmin) {
    return (
      <div className="max-w-xl mx-auto bg-white/80 backdrop-blur-md shadow-sm border border-white/20 rounded-2xl p-8 text-center">
        <div className="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
           <Shield className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-gray-900 mb-2">Access Denied</h3>
        <p className="text-gray-500">You do not have permission to view this page.</p>
      </div>
    );
  }

  const tabs = [
    { id: 'overlap', label: 'Overlap Settings', icon: Settings, component: AdminOverlapSettings },
    // { id: 'notifications', label: 'Notifications', icon: Bell, component: AdminNotificationSettings } // Example future tab
  ];

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 font-heading">Admin Settings</h1>
        <p className="text-gray-500 mt-1">Configure system-wide parameters and thresholds</p>
      </div>

      <div className="bg-white/80 backdrop-blur-md shadow-sm border border-white/20 rounded-2xl overflow-hidden min-h-[500px]">
        {/* Tabs Header */}
        <div className="border-b border-gray-100 flex p-2 bg-white/50 backdrop-blur-sm">
          {tabs.map((tab) => {
             const Icon = tab.icon;
             return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-xl transition-all ${
                  activeTab === tab.id
                    ? 'text-primary'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                {activeTab === tab.id && (
                  <motion.div
                    layoutId="activeTabSettings"
                    className="absolute inset-0 bg-white shadow-sm border border-gray-100 rounded-xl"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-2">
                   <Icon className="w-4 h-4" />
                   {tab.label}
                </span>
              </button>
             );
          })}
        </div>
        
        {/* Tab Content */}
        <div className="p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
               {ActiveComponent && <ActiveComponent />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

export default AdminSettings;