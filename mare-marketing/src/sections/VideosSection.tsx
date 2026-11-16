import { useState } from 'react';
import FadeIn from '../components/FadeIn';
import { VIDEOS, type Video } from '../data/videos';

function YouTubeCard({ video }: { video: Video }) {
  const [playing, setPlaying] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <div className="relative aspect-video overflow-hidden rounded-[28px] bg-dark">
        {playing ? (
          <iframe
            className="absolute inset-0 h-full w-full"
            src={`https://www.youtube-nocookie.com/embed/${video.id}?autoplay=1&rel=0`}
            title={video.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <button type="button" onClick={() => setPlaying(true)} className="group absolute inset-0 h-full w-full" aria-label={`Assistir: ${video.title}`}>
            <img
              src={`https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
            <span className="absolute inset-0 flex items-center justify-center bg-dark/20 transition-colors group-hover:bg-dark/10">
              <span className="flex h-16 w-16 items-center justify-center rounded-full bg-coral shadow-lg transition-transform group-hover:scale-110 md:h-20 md:w-20">
                <svg viewBox="0 0 24 24" className="ml-1 h-7 w-7 fill-dark md:h-8 md:w-8" aria-hidden="true">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </span>
            </span>
          </button>
        )}
      </div>
      <div className="flex flex-col gap-1 px-2">
        {video.client && <span className="text-xs uppercase tracking-widest text-coral sm:text-sm">{video.client}</span>}
        <h3 className="font-medium text-dark" style={{ fontSize: 'clamp(1rem, 1.6vw, 1.4rem)' }}>
          {video.title}
        </h3>
      </div>
    </div>
  );
}

export default function VideosSection() {
  if (VIDEOS.length === 0) return null;

  return (
    <section
      id="videos"
      className="relative z-20 -mt-10 rounded-t-[40px] bg-beige px-5 py-20 sm:-mt-12 sm:rounded-t-[50px] sm:px-8 sm:py-24 md:-mt-14 md:rounded-t-[60px] md:px-10 md:py-32"
    >
      <FadeIn as="h2" className="mb-6 text-center font-black uppercase leading-none tracking-tight text-dark" style={{ fontSize: 'clamp(3rem, 12vw, 160px)' }}>
        Vídeos
      </FadeIn>
      <FadeIn
        delay={0.1}
        className="mx-auto mb-16 max-w-[560px] text-center font-light leading-relaxed text-dark sm:mb-20 md:mb-28"
        style={{ fontSize: 'clamp(1rem, 2vw, 1.35rem)', opacity: 0.7 }}
      >
        Produção de vídeo pro YouTube: roteiro, gravação e edição feitos pela Maré.
      </FadeIn>
      <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-2 md:gap-10">
        {VIDEOS.map((video, i) => (
          <FadeIn key={video.id} delay={(i % 2) * 0.1}>
            <YouTubeCard video={video} />
          </FadeIn>
        ))}
      </div>
    </section>
  );
}
