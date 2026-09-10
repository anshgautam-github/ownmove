import React from 'react';

const testimonials = [
  {
    quote: "Discover surfaced a product internship I never would have searched for myself. The match was closer to my profile than anything on the usual job boards.",
    name: "Ananya Iyer",
    college: "SRM IST, KTR",
    year: "3rd Year",
    avatar: "https://images.unsplash.com/photo-1624610261655-777af2f586d7?w=50&h=50&fit=crop"
  },
  {
    quote: "Profile Analysis was blunt in the best way. It told me exactly what recruiters would flag before I applied anywhere, not after I got rejected.",
    name: "Rohan Deshmukh",
    college: "IIT Madras",
    year: "Final Year",
    avatar: "https://images.unsplash.com/photo-1694871420433-bf111bdfae07?w=50&h=50&fit=crop"
  },
  {
    quote: "The AI Coach felt like having a mentor on call. It walked me through interview prep and kept my Career Roadmap on track the whole way.",
    name: "Kavya Reddy",
    college: "VIT Vellore",
    year: "2nd Year",
    avatar: "https://images.unsplash.com/photo-1757351122515-21a7b61d682e?w=50&h=50&fit=crop"
  },
  {
    quote: "The Career Roadmap turned a vague 'get into product' goal into an actual month-by-month plan. I finally stopped guessing what to work on next.",
    name: "Aarav Sharma",
    college: "IIT Bombay",
    year: "2nd Year",
    avatar: "https://images.unsplash.com/photo-1575781023754-05115812f6bc?w=50&h=50&fit=crop"
  },
  {
    quote: "I found two certifications through the platform that recruiters actually asked about in my interviews. Didn't expect that from a discovery tool.",
    name: "Sneha Pillai",
    college: "NIT Trichy",
    year: "3rd Year",
    avatar: "https://images.unsplash.com/photo-1511763508683-99dc7949e97f?w=50&h=50&fit=crop"
  },
  {
    quote: "Found three hackathons in my first week that actually matched my skill level, not just the big-name ones everyone already knows about.",
    name: "Vikram Rao",
    college: "BITS Pilani",
    year: "Final Year",
    avatar: "https://images.unsplash.com/photo-1643213199610-5cc95a244387?w=50&h=50&fit=crop"
  },
  {
    quote: "As a first-year, I had no idea where to even start. The Programs section alone gave me a shortlist I could actually act on.",
    name: "Ishita Kapoor",
    college: "Manipal Institute of Technology",
    year: "1st Year",
    avatar: "https://images.unsplash.com/photo-1624610806209-82a4cbb4339a?w=50&h=50&fit=crop"
  },
  {
    quote: "Career Simulation let me try out a product role before committing to it. Saved me from switching majors over a decision I hadn't actually tested.",
    name: "Arjun Nair",
    college: "IIIT Hyderabad",
    year: "3rd Year",
    avatar: "https://images.unsplash.com/photo-1694871420666-d55d3649ea40?w=50&h=50&fit=crop"
  },
  {
    quote: "The Communities tab connected me with seniors who'd already been through the exact application process I was stuck on. That's worth more than any article.",
    name: "Meera Krishnan",
    college: "Delhi University",
    year: "2nd Year",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&h=50&fit=crop"
  },
  {
    quote: "Being able to track everything I'd applied to in one place stopped me from losing track of deadlines across a dozen different tabs.",
    name: "Karthik Subramanian",
    college: "PES University",
    year: "Final Year",
    avatar: "https://images.unsplash.com/photo-1575781023754-05115812f6bc?w=50&h=50&fit=crop"
  },
  {
    quote: "Profile Analysis pointed out gaps in my profile I'd never have noticed on my own. Fixed them before a single recruiter saw it.",
    name: "Divya Menon",
    college: "Anna University",
    year: "2nd Year",
    avatar: "https://images.unsplash.com/photo-1511763508683-99dc7949e97f?w=50&h=50&fit=crop"
  }
]

function TestimonialSection() {
  return (
    <section className="bg-[#0b0c16] py-12 lg:h-screen lg:min-h-[750px] overflow-hidden rounded-b-[40px] text-white relative flex flex-col justify-center shadow-[0_22px_54px_rgba(6,7,18,0.34)] sm:rounded-b-[56px]">
      <div className="max-w-[1300px] w-full mx-auto px-6 lg:px-8 relative z-10 shrink-0">
        <h2 className="text-[clamp(2rem,3vw,3rem)] font-bold text-white leading-[1.2] tracking-[-0.02em]">
          Helping thousands of students<br/>
          <span className="bg-gradient-to-r from-[#6b82ff] to-[#a259ff] text-transparent bg-clip-text">
            land the right opportunity
          </span>
        </h2>
      </div>

      <div className="relative w-full h-[220px] lg:h-[260px] lg:flex-grow flex items-center justify-center pointer-events-none shrink-0 my-2 lg:my-0">

        {/* SVG Wave lines */}
        <svg viewBox="0 0 1440 260" className="absolute w-full h-full object-cover">
          <defs>
            <linearGradient id="waveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#1e2c60" />
              <stop offset="60%" stopColor="#8138ff" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#a259ff" />
            </linearGradient>
          </defs>
          {/* Base Unbroken Lines */}
          {[...Array(12)].map((_, i) => (
            <path
              key={`base-${i}`}
              d={`M -100 ${120 + i*12} C 300 ${140 + i*12}, 600 ${200 + i*12}, 900 ${140 + i*12} C 1200 ${80 + i*12}, 1300 ${50 + i*12}, 1540 ${50 + i*12}`}
              fill="none"
              stroke="url(#waveGradient)"
              strokeWidth="1.5"
              style={{ opacity: 0.5 - (i*0.03) }}
            />
          ))}
          {/* Moving Energy Pulses over lines */}
          {[...Array(12)].map((_, i) => (
            <path
              key={`pulse-${i}`}
              className="wave-line-pulse"
              d={`M -100 ${120 + i*12} C 300 ${140 + i*12}, 600 ${200 + i*12}, 900 ${140 + i*12} C 1200 ${80 + i*12}, 1300 ${50 + i*12}, 1540 ${50 + i*12}`}
              fill="none"
              stroke="#b17aff"
              strokeWidth="2.5"
              style={{ opacity: 0.85 - (i*0.05), animationDelay: `${-i * 0.5}s` }}
            />
          ))}
        </svg>
      </div>

      {/* Testimonials Carousel */}
      <div className="max-w-[1300px] w-full mx-auto px-6 lg:px-8 mt-2 relative z-20 shrink-0">
        <div className="relative">
           {/* Two copies of the full 11-testimonial set, not six — the
               scroll animation moves the track by exactly -50% (see
               `.testimonial-track` in index.css), so it only loops
               seamlessly when the rendered list is two identical halves.
               With 11 unique cards now (up from 3), two copies already
               give a long scroll before it repeats; six would have meant
               66 DOM nodes for no visual benefit. */}
           <div className="flex overflow-hidden pb-6" style={{ maskImage: "linear-gradient(to right, transparent 0%, black 12%, black 88%, transparent 100%)", WebkitMaskImage: "linear-gradient(to right, transparent 0%, black 12%, black 88%, transparent 100%)" }}>
             <div className="testimonial-track gap-4 lg:gap-5">
               {[...testimonials, ...testimonials].map((testimonial, i) => (
                  <div key={i} className="testimonial-card-hover w-[300px] lg:w-[350px] shrink-0 bg-[#161829] rounded-[18px] p-5 lg:p-6 flex flex-col justify-between border border-white/5">
                    <p className="text-[#C1C6D4] text-[0.95rem] leading-[1.6] italic opacity-90">
                      "{testimonial.quote}"
                    </p>
                    <div className="mt-5 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                         <img src={testimonial.avatar} alt={testimonial.name} className="w-10 h-10 rounded-full object-cover" />
                         <div>
                           <div className="text-white font-medium text-[0.9rem] lg:text-[0.95rem]">{testimonial.name}</div>
                           <div className="text-[#4E5677] text-[0.75rem] mt-[1px]">{testimonial.college}</div>
                         </div>
                      </div>
                      <div className="text-[#4E5677] text-[0.75rem] text-right">{testimonial.year}</div>
                    </div>
                  </div>
               ))}
             </div>
           </div>
        </div>
      </div>
    </section>
  )
}

export default TestimonialSection;
