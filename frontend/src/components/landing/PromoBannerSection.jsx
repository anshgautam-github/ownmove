import React from 'react';

function PromoBannerSection() {
  return (
    <section className="bg-white py-12 px-6 lg:px-8 flex flex-col items-center">
      <div className="w-full max-w-[1100px] rounded-[24px] overflow-hidden relative shadow-md min-h-[260px] flex flex-col md:flex-row items-center border border-gray-100">
        
        {/* Abstract Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#DD4A3D] via-[#B83471] to-[#4030BD] z-0" />
        
        {/* Left Side: Logo */}
        <div className="relative z-10 flex flex-col items-center justify-center py-10 px-8 w-full md:w-auto md:min-w-[340px]">
          <div className="font-bold text-white tracking-tighter leading-none drop-shadow-md relative">
            <div className="text-[3.8rem] tracking-[-0.04em] font-semibold">OwnMove</div>
            <div className="text-[4.8rem] leading-[0.75] ml-[3.5rem] mt-1">PRO</div>
          </div>
        </div>

        {/* Right Side: Content */}
        <div className="relative z-10 flex-grow px-8 md:px-12 py-10 flex flex-col text-white">
          <div className="text-[0.95rem] font-medium text-white/90">
            For verified students <span className="opacity-50 mx-1.5">•</span> Limited-time offer
          </div>

          <div className="w-full h-px bg-white/20 mt-3 mb-5" />

          <h3 className="text-[1.85rem] font-bold tracking-tight drop-shadow-sm mb-6">
            Get your first month of OwnMove Pro free.
          </h3>

          <div className="flex flex-wrap gap-4">
            <button className="bg-[#3B42E7] hover:bg-[#2b33c0] text-white px-7 py-2.5 rounded-full text-[0.95rem] font-medium transition-colors shadow-md">
              Start free trial
            </button>
            <button className="bg-white/10 hover:bg-white/20 text-white backdrop-blur-md border border-white/20 px-7 py-2.5 rounded-full text-[0.95rem] font-medium transition-colors shadow-sm">
              See what&apos;s included
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

export default PromoBannerSection;