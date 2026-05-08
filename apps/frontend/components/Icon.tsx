import type React from 'react';

type IconName = 'home' | 'sparkle' | 'compass' | 'bookmark' | 'user' | 'search' | 'filter' | 'sort' | 'chevronDown' | 'x' | 'check' | 'edit' | 'trash' | 'link' | 'shield' | 'paper' | 'building' | 'tag' | 'arrowRight' | 'arrowLeft' | 'save' | 'eye' | 'plus' | 'menu' | 'close';

export function Icon({ name, size = 16, className }: { name: IconName; size?: number; className?: string }) {
  const common = { width: size, height: size, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', strokeWidth: 1.5, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, className };
  const paths: Record<IconName, React.ReactNode> = {
    home: <><path d="M2.5 7L8 2.5 13.5 7"/><path d="M3.5 6.5v7h9v-7"/><path d="M6.5 13.5V9h3v4.5"/></>,
    sparkle: <><path d="M8 2v3M8 11v3M2 8h3M11 8h3M3.8 3.8l2 2M10.2 10.2l2 2M12.2 3.8l-2 2M5.8 10.2l-2 2"/></>,
    compass: <><circle cx="8" cy="8" r="5.5"/><path d="M10.2 5.8L9 9l-3.2 1.2L7 7z"/></>,
    bookmark: <path d="M4.5 2.5h7v11l-3.5-2-3.5 2z"/>,
    user: <><circle cx="8" cy="5.5" r="2.5"/><path d="M2.5 13.5c0-2.5 2.4-4.5 5.5-4.5s5.5 2 5.5 4.5"/></>,
    search: <><circle cx="7" cy="7" r="4"/><path d="M10.2 10.2L14 14"/></>,
    filter: <path d="M2 3.5h12l-4.5 5.5v4.5l-3-1.5v-3z"/>,
    sort: <><path d="M4 2.5v11M2 5.5l2-3 2 3M12 13.5V2.5M10 10.5l2 3 2-3"/></>,
    chevronDown: <path d="M4 6l4 4 4-4"/>,
    x: <><path d="M4 4l8 8M12 4l-8 8"/></>,
    check: <path d="M3 8.5L6.5 12 13 4.5"/>,
    edit: <><path d="M2.5 13.5L3 11l7.5-7.5 2 2L5 13z"/><path d="M10.5 3.5l2 2"/></>,
    trash: <><path d="M3 4.5h10"/><path d="M5 4.5V3h6v1.5"/><path d="M4 4.5L4.5 13.5h7L12 4.5"/><path d="M7 7v4M9 7v4"/></>,
    link: <><path d="M9 4.5h2.5a2 2 0 010 4H10M7 11.5H4.5a2 2 0 010-4H6M5.5 8h5"/></>,
    shield: <path d="M8 2l5 2v4c0 3-2.2 5.2-5 6-2.8-.8-5-3-5-6V4z"/>,
    paper: <><path d="M4 2h6l2 2v10H4z"/><path d="M10 2v2h2"/><path d="M6.5 7h3M6.5 9.5h3M6.5 12h2"/></>,
    building: <><path d="M3 13.5V5l5-2.5L13 5v8.5"/><path d="M3 13.5h10"/><path d="M6 13.5v-3h4v3"/><path d="M6.5 7h1M9 7h1M6.5 9h1M9 9h1"/></>,
    tag: <><path d="M2.5 8.5L8.5 2.5h5v5L7.5 13.5z"/><circle cx="11" cy="5" r=".7" fill="currentColor" stroke="none"/></>,
    arrowRight: <><path d="M3 8h10M9 4l4 4-4 4"/></>,
    arrowLeft: <><path d="M13 8H3M7 4L3 8l4 4"/></>,
    save: <path d="M4.5 2.5h7v11l-3.5-2-3.5 2z"/>,
    eye: <><path d="M1.8 8s2.3-4 6.2-4 6.2 4 6.2 4-2.3 4-6.2 4-6.2-4-6.2-4z"/><circle cx="8" cy="8" r="1.8"/></>,
    plus: <><path d="M8 3v10M3 8h10"/></>,
    menu: <><path d="M3 4h10M3 8h10M3 12h10"/></>,
    close: <><path d="M4 4l8 8M12 4l-8 8"/></>,
  };
  return <svg {...common}>{paths[name]}</svg>;
}
