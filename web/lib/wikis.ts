// Mirrors pipeline/rules.py TRACKED_WIKIS.
export const WIKIS: Record<string, { name: string; native: string }> = {
  enwiki: { name: "English", native: "English" },
  hiwiki: { name: "Hindi", native: "हिन्दी" },
  mrwiki: { name: "Marathi", native: "मराठी" },
  bnwiki: { name: "Bengali", native: "বাংলা" },
  tawiki: { name: "Tamil", native: "தமிழ்" },
  tewiki: { name: "Telugu", native: "తెలుగు" },
  knwiki: { name: "Kannada", native: "ಕನ್ನಡ" },
  mlwiki: { name: "Malayalam", native: "മലയാളം" },
  guwiki: { name: "Gujarati", native: "ગુજરાતી" },
  pawiki: { name: "Punjabi", native: "ਪੰਜਾਬੀ" },
  urwiki: { name: "Urdu", native: "اردو" },
};

export const INDIAN_WIKIS = Object.keys(WIKIS).filter((w) => w !== "enwiki");

export function wikiName(wiki: string): string {
  return WIKIS[wiki]?.name ?? wiki;
}

export function wikiLang(wiki: string): string {
  return wiki.endsWith("wiki") ? wiki.slice(0, -4) : wiki;
}

export function articleUrl(wiki: string, title: string): string {
  return `https://${wikiLang(wiki)}.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(" ", "_"))}`;
}

export function topicHref(wiki: string, title: string): string {
  return `/topic/${wiki}/${encodeURIComponent(title)}`;
}
