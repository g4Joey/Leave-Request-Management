import React from 'react';
import { motion } from 'framer-motion';

const LoginBranding = () => {
  return (
    <div className="w-full h-full relative overflow-hidden flex flex-col justify-between p-12 text-white">
      <div className="relative z-10">
        <div className="flex items-center text-2xl font-bold font-heading">
          {/* Logo */}
          <img src="/leavemateLogo.png" alt="leavemateLogo" className='h-20 w-20' />
          LeaveMates
        </div>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="mt-20"
        >
          <h1 className="text-5xl font-bold mb-6 leading-tight">
            Simplify Your <br />
            <span className="text-accent">Leave Management</span>
          </h1>
          <p className="text-xl text-primary-100 max-w-md leading-relaxed">
            Streamline employee time-off requests, approvals, and tracking in one unified platform.
          </p>
        </motion.div>
      </div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
        className="relative z-10"
      >
        <p className="text-sm text-primary-200">© 2025 LeaveMates. All rights reserved.</p>
      </motion.div>
      
      {/* Abstract Shapes */}
      <motion.div 
         animate={{ rotate: 360 }}
         transition={{ duration: 100, repeat: Infinity, ease: "linear" }}
         className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 rounded-full bg-white/5 blur-3xl" 
      />
      <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-80 h-80 rounded-full bg-accent/20 blur-3xl"></div>
    </div>
  );
};

export default LoginBranding;
