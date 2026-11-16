import { WHATSAPP_URL } from '../constants';

export default function ContactButton() {
  return (
    <a
      href={WHATSAPP_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-block rounded-full bg-coral px-8 py-3 text-xs font-semibold uppercase tracking-widest text-dark transition-transform duration-200 hover:-translate-y-0.5 sm:px-10 sm:py-3.5 sm:text-sm md:px-12 md:py-4 md:text-base"
    >
      Falar com Especialista
    </a>
  );
}
