import FadeIn from '../components/FadeIn';
import Magnet from '../components/Magnet';
import ContactButton from '../components/ContactButton';
import MareMark from '../components/MareMark';
import { WHATSAPP_URL } from '../constants';
import heroShapes from '../assets/hero-shapes.webp';
import { VIDEOS } from '../data/videos';

const NAV_LINKS: { label: string; href: string; external?: boolean }[] = [
  { label: 'Serviços', href: '#services' },
  { label: 'Clientes', href: '#clients' },
  ...(VIDEOS.length > 0 ? [{ label: 'Vídeos', href: '#videos' }] : []),
  { label: 'Contato', href: WHATSAPP_URL, external: true },
];

export default function HeroSection() {
  return (
    <section className="relative h-screen flex flex-col" style={{ overflowX: 'clip', overflowY: 'clip' }}>
      <FadeIn as="nav" delay={0} y={-20} className="flex items-center justify-between px-6 md:px-10 pt-6 md:pt-8">
        <div className="flex shrink-0 items-center gap-2">
          <MareMark className="h-6 w-6 text-warm-white md:h-7 md:w-7" />
          <span className="text-sm font-semibold uppercase tracking-[0.2em] text-warm-white md:text-base">Maré</span>
        </div>
        <div className="flex gap-4 sm:gap-6 md:gap-10">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              {...(link.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
              className="text-xs sm:text-sm md:text-lg lg:text-[1.4rem] font-medium uppercase tracking-wider text-beige transition-opacity duration-200 hover:opacity-70"
            >
              {link.label}
            </a>
          ))}
        </div>
      </FadeIn>

      <div className="flex-1 flex flex-col justify-end relative">
        <div className="overflow-hidden w-full">
          <FadeIn
            as="h1"
            onMount
            delay={0.15}
            y={40}
            className="hero-heading mt-6 sm:mt-4 md:-mt-5 w-full whitespace-nowrap text-[10vw] font-black uppercase leading-none tracking-tight sm:text-[11vw] md:text-[12vw] lg:text-[13vw]"
          >
            Essa é a maré
          </FadeIn>
        </div>
        <div className="relative z-20 flex items-end justify-between px-6 pb-7 sm:pb-8 md:px-10 md:pb-10">
          <FadeIn
            delay={0.35}
            y={20}
            className="max-w-[160px] font-light uppercase tracking-wide leading-snug text-beige sm:max-w-[220px] md:max-w-[260px]"
            style={{ fontSize: 'clamp(0.75rem, 1.4vw, 1.5rem)' }}
          >
            tráfego pago e redes sociais que colocam sua marca na frente de quem compra
          </FadeIn>
          <FadeIn delay={0.5} y={20}>
            <ContactButton />
          </FadeIn>
        </div>
      </div>

      <div className="pointer-events-none absolute left-1/2 top-1/2 z-10 w-[280px] -translate-x-1/2 -translate-y-1/2 sm:top-auto sm:bottom-0 sm:translate-y-0 sm:w-[360px] md:w-[440px] lg:w-[520px]">
        <FadeIn delay={0.6} y={30} className="pointer-events-auto">
          <Magnet padding={150} strength={3} activeTransition="transform 0.3s ease-out" inactiveTransition="transform 0.6s ease-in-out">
            <img src={heroShapes} alt="Maré Marketing" className="h-auto w-full select-none" draggable={false} />
          </Magnet>
        </FadeIn>
      </div>
    </section>
  );
}
