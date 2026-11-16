import HeroSection from './sections/HeroSection';
import MarqueeSection from './sections/MarqueeSection';
import AboutSection from './sections/AboutSection';
import ServicesSection from './sections/ServicesSection';
import ClientsSection from './sections/ClientsSection';
import VideosSection from './sections/VideosSection';

export default function App() {
  return (
    <div className="bg-dark" style={{ overflowX: 'clip', overflowY: 'clip' }}>
      <HeroSection />
      <MarqueeSection />
      <AboutSection />
      <ServicesSection />
      <ClientsSection />
      <VideosSection />
    </div>
  );
}
