export interface Video {
  /** YouTube video id, e.g. the "dQw4w9WgXcQ" in youtube.com/watch?v=dQw4w9WgXcQ */
  id: string;
  title: string;
  client?: string;
}

export const VIDEOS: Video[] = [];
