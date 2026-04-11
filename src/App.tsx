/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "@/components/ui/button";
import { Monitor, MousePointer2 } from "lucide-react";

export default function App() {
  const [showHello, setShowHello] = useState(false);

  return (
    <div className="min-h-screen bg-[#f5f5f5] flex items-center justify-center p-4 font-sans">
      {/* Desktop Window Container */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden"
      >
        {/* Window Header */}
        <div className="bg-gray-50 border-bottom border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Monitor className="w-4 h-4 text-gray-500" />
            <span className="text-xs font-medium text-gray-600 uppercase tracking-wider">Desktop App</span>
          </div>
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-gray-200" />
            <div className="w-3 h-3 rounded-full bg-gray-200" />
            <div className="w-3 h-3 rounded-full bg-gray-200" />
          </div>
        </div>

        {/* Window Content */}
        <div className="p-12 flex flex-col items-center justify-center gap-8 min-h-[300px]">
          <AnimatePresence mode="wait">
            {showHello ? (
              <motion.div
                key="hello"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="text-6xl font-light tracking-tighter text-gray-900"
              >
                Hello
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-center"
              >
                <p className="text-gray-400 text-sm mb-2">Click the button below</p>
                <MousePointer2 className="w-6 h-6 text-gray-300 mx-auto animate-bounce" />
              </motion.div>
            )}
          </AnimatePresence>

          <Button 
            size="lg" 
            onClick={() => setShowHello(!showHello)}
            className="rounded-full px-8 py-6 text-lg font-medium transition-all hover:scale-105 active:scale-95"
          >
            {showHello ? "Reset" : "Say Hello"}
          </Button>
        </div>

        {/* Window Footer */}
        <div className="bg-gray-50 border-t border-gray-100 px-6 py-3 text-center">
          <p className="text-[10px] text-gray-400 uppercase tracking-[0.2em]">Powered by Google AI Studio</p>
        </div>
      </motion.div>
    </div>
  );
}
