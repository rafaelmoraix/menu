import FadeIn from '../components/FadeIn';
import Dot from '../components/Dot';

const SERVICES = [
  {
    name: 'Tráfego Pago',
    description:
      'Campanhas no Meta Ads e no Google Ads pra colocar sua empresa na frente de quem já procura pelo que você vende, com acompanhamento de cada real investido.',
  },
  {
    name: 'Gestão de Redes Sociais',
    description:
      'Planejamento, criação de conteúdo e gestão diária do seu Instagram e das suas redes, pra sua marca crescer com constância e conversar com quem importa.',
  },
  {
    name: 'Produção de Vídeo',
    description:
      'Roteiro, gravação e edição de vídeos pro YouTube e pras redes, do conteúdo do dia a dia às produções maiores.',
  },
  {
    name: 'Sites & Landing Pages',
    description: 'Sites institucionais, páginas de vendas e projetos personalizados focados em conversão.',
  },
  {
    name: 'Aplicativos Personalizados',
    description:
      'Sistemas sob medida pra sua empresa -- área do cliente, agendamento, pedidos, gestão interna e acompanhamento de serviço, tudo em um só lugar.',
  },
  {
    name: 'Automação de Atendimento',
    description: 'WhatsApp, captação de leads, resposta automática e acompanhamento de cliente, sem ninguém ficar esquecido.',
  },
  {
    name: 'Gestão de Caixa & Cobrança',
    description:
      'Organizamos seu caixa, sua cobrança e seus recebimentos, pra você saber exatamente quanto entra, quanto sai, e quanto sua empresa realmente ganha.',
  },
];

const DOT_COLORS = ['#FF5C35', '#3157D5', '#39A86B'];

export default function ServicesSection() {
  return (
    <section
      id="services"
      className="rounded-t-[40px] bg-beige px-5 py-20 sm:rounded-t-[50px] sm:px-8 sm:py-24 md:rounded-t-[60px] md:px-10 md:py-32"
    >
      <FadeIn as="h2" className="mb-16 text-center font-black uppercase leading-none tracking-tight text-dark sm:mb-20 md:mb-28" style={{ fontSize: 'clamp(3rem, 12vw, 160px)' }}>
        Serviços
      </FadeIn>
      <div className="mx-auto max-w-5xl" style={{ borderBottom: '1px solid rgba(17, 24, 39, 0.15)' }}>
        {SERVICES.map((service, i) => (
          <FadeIn
            key={service.name}
            delay={i * 0.1}
            className="flex items-start gap-6 py-8 sm:gap-10 sm:py-10 md:py-12"
            style={{ borderTop: '1px solid rgba(17, 24, 39, 0.15)' }}
          >
            <span className="flex-shrink-0 font-black leading-none text-dark" style={{ fontSize: 'clamp(3rem, 10vw, 140px)' }}>
              {String(i + 1).padStart(2, '0')}
            </span>
            <div className="flex flex-col gap-3">
              <h3 className="flex items-center gap-3 font-medium uppercase text-dark" style={{ fontSize: 'clamp(1rem, 2.2vw, 2.1rem)' }}>
                <Dot className="h-2.5 w-2.5 flex-shrink-0" color={DOT_COLORS[i % DOT_COLORS.length]} />
                {service.name}
              </h3>
              <p className="max-w-2xl font-light leading-relaxed text-dark" style={{ fontSize: 'clamp(0.85rem, 1.6vw, 1.25rem)', opacity: 0.6 }}>
                {service.description}
              </p>
            </div>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}
