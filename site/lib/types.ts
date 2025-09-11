export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

export interface BenchPressData {
  date: string;
  set: number;
  weight: number;
  reps: number;
}

export interface ChartData {
  dates: string[];
  series: Array<{
    name: string;
    type: string;
    smooth: boolean;
    data: (number | null)[];
    connectNulls: boolean;
  }>;
}
