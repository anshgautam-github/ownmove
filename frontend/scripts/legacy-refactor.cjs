const fs = require('fs');
const path = './src/App.jsx';
const lines = fs.readFileSync(path, 'utf8').split('\n');

const getLines = (start, end) => lines.slice(start - 1, end).join('\n');

const components = [
  {
    name: 'HeroSection',
    content: "import React, { useEffect, useRef, useState } from 'react';\n\n" +
             getLines(3, 18) + '\n\n' +
             getLines(235, 351) + '\n\n' +
             "export default HeroSection;"
  },
  {
    name: 'IntelligenceSection',
    content: "import React, { useEffect, useRef, useState } from 'react';\n\n" +
             getLines(19, 148) + '\n\n' +
             getLines(190, 233) + '\n\n' +
             getLines(475, 621) + '\n\n' +
             "export default IntelligenceSection;"
  },
  {
    name: 'WorkAiSection',
    content: "import React from 'react';\n\n" +
             getLines(353, 473) + '\n\n' +
             "export default WorkAiSection;"
  },
  {
    name: 'HowItWorksSection',
    content: "import React, { useEffect, useRef, useState } from 'react';\n\n" +
             getLines(150, 179) + '\n\n' +
             getLines(623, 783) + '\n\n' +
             "export default HowItWorksSection;"
  },
  {
    name: 'FounderSection',
    content: "import React from 'react';\n\n" +
             getLines(181, 188) + '\n\n' +
             getLines(785, 902) + '\n\n' +
             "export default FounderSection;"
  },
  {
    name: 'StatsBannerSection',
    content: "import React from 'react';\n\n" +
             getLines(904, 988) + '\n\n' +
             "export default StatsBannerSection;"
  },
  {
    name: 'TestimonialSection',
    content: "import React from 'react';\n\n" +
             getLines(990, 1127) + '\n\n' +
             "export default TestimonialSection;"
  },
  {
    name: 'FaqSection',
    content: "import React, { useState } from 'react';\n\n" +
             getLines(1129, 1233) + '\n\n' +
             "export default FaqSection;"
  },
  {
    name: 'WorkAiFeaturesSection',
    content: "import React from 'react';\n\n" +
             getLines(1235, 1345) + '\n\n' +
             "export default WorkAiFeaturesSection;"
  },
  {
    name: 'PromoBannerSection',
    content: "import React from 'react';\n\n" +
             getLines(1347, 1388) + '\n\n' +
             "export default PromoBannerSection;"
  },
  {
    name: 'FooterSection',
    content: "import React from 'react';\n\n" +
             getLines(1390, 1536) + '\n\n' +
             "export default FooterSection;"
  }
];

if (!fs.existsSync('./src/components')) {
  fs.mkdirSync('./src/components');
}

components.forEach(comp => {
  fs.writeFileSync('./src/components/' + comp.name + '.jsx', comp.content);
});

const newAppJsx = [
  "import React from 'react';",
  "import HeroSection from './components/HeroSection';",
  "import WorkAiSection from './components/WorkAiSection';",
  "import IntelligenceSection from './components/IntelligenceSection';",
  "import HowItWorksSection from './components/HowItWorksSection';",
  "import FounderSection from './components/FounderSection';",
  "import StatsBannerSection from './components/StatsBannerSection';",
  "import TestimonialSection from './components/TestimonialSection';",
  "import FaqSection from './components/FaqSection';",
  "import WorkAiFeaturesSection from './components/WorkAiFeaturesSection';",
  "import PromoBannerSection from './components/PromoBannerSection';",
  "import FooterSection from './components/FooterSection';",
  "",
  "function App() {",
  "  return (",
  "    <main className=\"bg-[#06070f]\">",
  "      <HeroSection />",
  "      <WorkAiSection />",
  "      <IntelligenceSection />",
  "      <HowItWorksSection />",
  "      <FounderSection />",
  "      <StatsBannerSection />",
  "      <TestimonialSection />",
  "      <FaqSection />",
  "      <WorkAiFeaturesSection />",
  "      <PromoBannerSection />",
  "      <FooterSection />",
  "    </main>",
  "  );",
  "}",
  "",
  "export default App;",
  ""
].join('\\n');

fs.writeFileSync(path, newAppJsx);
console.log('Refactoring complete.');
