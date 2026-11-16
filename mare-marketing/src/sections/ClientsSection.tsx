import FadeIn from '../components/FadeIn';
import logo153 from '../assets/clients/153filmes.webp';
import logoCarcoating from '../assets/clients/carcoating.webp';
import logoRecife from '../assets/clients/recife-ordinario.webp';

interface Client {
  name: string;
  segment: string;
  description: string;
  logo: string;
  /** Background behind the logo, matching the logo file's own background. */
  tileColor: string;
  /** 'contain' keeps a wordmark whole; 'cover' fills the tile with a square avatar. */
  fit: 'contain' | 'cover';
}

const CLIENTS: Client[] = [
  {
    name: '153 Filmes',
    segment: 'Produtora',
    description: 'Produtora brasileira que transmite o The Golf Brasil na Band.',
    logo: logo153,
    tileColor: '#000000',
    fit: 'contain',
  },
  {
    name: 'Carcoating',
    segment: 'Estética automotiva',
    description: 'A maior loja de estética automotiva do Brasil.',
    logo: logoCarcoating,
    tileColor: '#ffffff',
    fit: 'contain',
  },
  {
    name: 'Recife Ordinário',
    segment: 'Notícias',
    description: 'A maior página de notícias do Nordeste.',
    logo: logoRecife,
    tileColor: '#b0124f',
    fit: 'cover',
  },
];

export default function ClientsSection() {
  return (
    <section
      id="clients"
      className="relative z-10 -mt-10 rounded-t-[40px] bg-dark px-5 py-20 sm:-mt-12 sm:rounded-t-[50px] sm:px-8 sm:py-24 md:-mt-14 md:rounded-t-[60px] md:px-10 md:py-32"
    >
      <FadeIn as="h2" className="hero-heading mb-6 text-center font-black uppercase leading-none tracking-tight" style={{ fontSize: 'clamp(3rem, 12vw, 160px)' }}>
        Clientes
      </FadeIn>
      <FadeIn
        delay={0.1}
        className="mx-auto mb-16 max-w-[560px] text-center font-light leading-relaxed text-beige sm:mb-20 md:mb-28"
        style={{ fontSize: 'clamp(1rem, 2vw, 1.35rem)', opacity: 0.8 }}
      >
        Marcas que confiam na Maré pra crescer no digital.
      </FadeIn>

      <div className="mx-auto grid max-w-6xl gap-5 sm:gap-6 md:grid-cols-3">
        {CLIENTS.map((client, i) => (
          <FadeIn
            key={client.name}
            delay={i * 0.1}
            className="flex flex-col gap-5 rounded-[32px] border-2 border-beige/20 p-4 transition-colors duration-200 hover:border-beige/50 sm:p-5"
          >
            <div
              className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-[24px]"
              style={{ backgroundColor: client.tileColor, padding: client.fit === 'contain' ? '12%' : 0 }}
            >
              <img
                src={client.logo}
                alt={`Logo ${client.name}`}
                loading="lazy"
                className={client.fit === 'contain' ? 'max-h-full w-full object-contain' : 'h-full w-full object-cover'}
              />
            </div>
            <div className="flex flex-col gap-2 px-2 pb-2">
              <span className="text-xs uppercase tracking-widest text-coral sm:text-sm">{client.segment}</span>
              <h3 className="font-medium uppercase text-warm-white" style={{ fontSize: 'clamp(1.1rem, 1.8vw, 1.6rem)' }}>
                {client.name}
              </h3>
              <p className="font-light leading-relaxed text-beige" style={{ fontSize: 'clamp(0.9rem, 1.2vw, 1.05rem)', opacity: 0.7 }}>
                {client.description}
              </p>
            </div>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}
