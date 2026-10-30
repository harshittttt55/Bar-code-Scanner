import { useState, useRef, useEffect, useCallback } from 'react';
import styled, { keyframes, css } from 'styled-components';
import axios from 'axios';

// ── Animations ────────────────────────────────────────────────────────────────

const fadeInUp = keyframes`
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
`;

const pulseAnim = keyframes`
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
`;

const shimmer = keyframes`
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
`;

const spin = keyframes`
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
`;

// ── Design tokens ─────────────────────────────────────────────────────────────
const CLR = {
  green:  '#10b981',
  greenDim: 'rgba(16,185,129,0.12)',
  greenBorder: 'rgba(16,185,129,0.25)',
  purple: '#8b5cf6',
  purpleDim: 'rgba(139,92,246,0.12)',
  purpleBorder: 'rgba(139,92,246,0.3)',
  red:    '#ef4444',
  yellow: '#f59e0b',
  card:   'rgba(17,24,39,0.85)',
  input:  'rgba(15,23,42,0.7)',
  border: 'rgba(99,102,241,0.15)',
  text:   '#f1f5f9',
  muted:  '#64748b',
  sub:    '#94a3b8',
};

// ── Shared base styles ────────────────────────────────────────────────────────

const Wrapper = styled.div`animation: ${fadeInUp} 0.35s ease forwards;`;

const Card = styled.div`
  background: ${CLR.card};
  border: 1px solid ${p => p.border || CLR.border};
  border-radius: 20px;
  padding: 28px 32px;
  margin-bottom: 20px;
  backdrop-filter: blur(12px);
  transition: border-color 0.25s;
  @media(max-width:500px){ padding: 20px 16px; }
`;

const AnimatedCard = styled(Card)`
  animation: ${fadeInUp} 0.35s ease forwards;
`;

const SpinnerIcon = styled.span`
  width: 14px;
  height: 14px;
  border: 2px solid #fff;
  border-top-color: transparent;
  border-radius: 50%;
  display: inline-block;
  animation: ${spin} 0.7s linear infinite;
`;

const Label = styled.label`
  display: block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: ${p => p.color || CLR.green};
  margin-bottom: 12px;
`;

const BaseInput = styled.input`
  width: 100%;
  background: ${CLR.input};
  border: 1px solid ${p => p.borderColor || CLR.greenBorder};
  border-radius: 12px;
  padding: 13px 16px;
  color: ${CLR.text};
  font-size: 0.95rem;
  font-family: 'Inter', sans-serif;
  outline: none;
  transition: all 0.2s;
  &::placeholder { color: #334155; }
  &:focus {
    border-color: ${p => p.focusColor || CLR.green};
    box-shadow: 0 0 0 3px ${p => p.glowColor || 'rgba(16,185,129,0.1)'};
    background: rgba(15,23,42,0.9);
  }
  &:disabled { opacity: 0.55; cursor: not-allowed; }
`;

const Btn = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  border-radius: 12px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  padding: ${p => p.sm ? '7px 14px' : '13px 24px'};
  background: ${p => p.bg || 'linear-gradient(135deg,#059669,#10b981)'};
  color: #fff;
  &:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.08); }
  &:active:not(:disabled) { transform: translateY(0); }
  &:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
`;

const GhostBtn = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: ${p => p.sm ? '5px 10px' : '8px 14px'};
  border-radius: 9px;
  border: 1px solid ${p => p.borderColor || CLR.border};
  background: transparent;
  color: ${p => p.color || CLR.sub};
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s;
  &:hover:not(:disabled) {
    background: ${p => p.hoverBg || 'rgba(99,102,241,0.08)'};
    color: ${p => p.hoverColor || CLR.text};
    border-color: ${p => p.hoverBorder || 'rgba(99,102,241,0.35)'};
  }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
`;

const Chips = styled.div`
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
`;

const Chip = styled.button`
  background: ${p => p.bg || CLR.greenDim};
  border: 1px solid ${p => p.borderColor || CLR.greenBorder};
  border-radius: 100px;
  padding: 4px 12px;
  font-size: 0.73rem;
  color: ${p => p.color || CLR.green};
  cursor: pointer;
  transition: all 0.18s;
  font-weight: 500;
  &:hover:not(:disabled) { filter: brightness(1.2); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
`;

const ModeBadge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: ${p => p.bg || CLR.greenDim};
  border: 1px solid ${p => p.borderColor || CLR.greenBorder};
  border-radius: 100px;
  padding: 3px 12px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: ${p => p.color || CLR.green};
  margin-bottom: 16px;
`;

const Disclaimer = styled.div`
  margin-top: 18px;
  background: rgba(245,158,11,0.06);
  border: 1px solid rgba(245,158,11,0.2);
  border-radius: 10px;
  padding: 11px 15px;
  font-size: 0.76rem;
  color: #fbbf24;
  line-height: 1.6;
`;

const LoadingDots = styled.div`
  display: flex; gap: 6px; align-items: center;
  padding: 28px 0; justify-content: center;
  span {
    width: 8px; height: 8px; border-radius: 50%;
    background: ${CLR.green};
    animation: ${pulseAnim} 1.2s ease-in-out infinite;
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
`;

const ErrorBox = styled.div`
  background: rgba(239,68,68,0.06);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 14px;
  padding: 20px 24px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  animation: ${fadeInUp} 0.3s ease forwards;
`;

// ── Markdown renderer ─────────────────────────────────────────────────────────

const MarkdownBlock = styled.div`
  font-size: 0.9rem; line-height: 1.8; color: #cbd5e1;
  h1,h2 { color: #f1f5f9; font-family:'Space Grotesk',sans-serif; margin: 18px 0 8px; }
  h2 { font-size: 1rem; }
  h3 { color: #a5b4fc; font-size: 0.92rem; margin: 14px 0 6px; }
  p  { margin-bottom: 10px; }
  ul,ol { padding-left: 20px; margin-bottom: 10px; }
  li { margin-bottom: 4px; }
  strong { color: #e2e8f0; }
  em { color: #94a3b8; }
  a  { color: ${CLR.green}; }
  hr { border: none; border-top: 1px solid rgba(99,102,241,0.15); margin: 14px 0; }
  table { width:100%; border-collapse:collapse; margin:12px 0; font-size:0.83rem; overflow-x:auto; display:block; }
  th { background:${CLR.greenDim}; color:${CLR.green}; padding:9px 13px; text-align:left; border:1px solid ${CLR.greenBorder}; white-space:nowrap; }
  td { padding:8px 13px; border:1px solid rgba(99,102,241,0.12); vertical-align:top; }
  tr:nth-child(even) td { background:rgba(15,23,42,0.3); }
`;

function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
    .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^---$/gm, '<hr/>')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1 ↗</a>')
    .replace(/\n\n(?!<)/g, '</p><p>')
    .replace(/\n(?!<)/g, '<br/>');
  html = html.replace(/((?:<li>.*?<\/li>\s*)+)/gs, '<ul>$1</ul>');
  html = html.replace(/((?:^\|.+\|\s*\n)+)/gm, tableBlock => {
    const lines = tableBlock.trim().split('\n').filter(l => l.trim());
    if (lines.length < 2) return tableBlock;
    const toRow = (line, tag) =>
      '<tr>' + line.split('|').slice(1,-1).map(c=>`<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
    const [header,, ...body] = lines;
    return `<table><thead>${toRow(header,'th')}</thead><tbody>${body.map(l=>toRow(l,'td')).join('')}</tbody></table>`;
  });
  return `<p>${html}</p>`;
}

// ── Autocomplete input ────────────────────────────────────────────────────────

const SUGGESTIONS = [
  'Paracetamol 500mg','Dolo 650','Calpol 500','Ibuprofen 400mg','Brufen 400',
  'Azithromycin 500mg','Amoxicillin 500mg','Augmentin 625','Metformin 500mg',
  'Glycomet 500','Atorvastatin 10mg','Lipitor 10mg','Pantoprazole 40mg',
  'Pan 40','Omeprazole 20mg','Cetirizine 10mg','Allegra 120mg','Montair LC',
  'Ciprofloxacin 500mg','Levofloxacin 500mg','Aspirin 75mg','Ecosprin 75',
  'Losartan 50mg','Amlodipine 5mg','Metoprolol 25mg','Telmisartan 40mg',
];

const SuggestBox = styled.div`
  position: absolute;
  top: calc(100% + 4px);
  left: 0; right: 0;
  background: #0f172a;
  border: 1px solid ${p => p.accentBorder || CLR.greenBorder};
  border-radius: 12px;
  z-index: 100;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
`;

const SuggestItem = styled.div`
  padding: 10px 14px;
  font-size: 0.875rem;
  color: ${p => p.active ? CLR.text : CLR.sub};
  background: ${p => p.active ? 'rgba(99,102,241,0.12)' : 'transparent'};
  cursor: pointer;
  transition: background 0.15s;
  &:hover { background: rgba(99,102,241,0.1); color: ${CLR.text}; }
`;

const InputWrap = styled.div`position: relative;`;

function AutoInput({ value, onChange, onSelect, placeholder, disabled, accentBorder, focusColor, glowColor }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const ref = useRef(null);

  const filtered = value.trim().length > 0
    ? SUGGESTIONS.filter(s => s.toLowerCase().includes(value.toLowerCase())).slice(0, 6)
    : [];

  useEffect(() => {
    setActive(-1);
    setOpen(filtered.length > 0);
  }, [value, filtered.length]);

  useEffect(() => {
    const handler = e => { if (!ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const pick = s => { onSelect(s); setOpen(false); };

  const onKey = e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (open && active >= 0) {
        pick(filtered[active]);
      } else if (value.trim()) {
        // lock whatever the user typed, even if not in suggestions
        pick(value.trim());
      }
      return;
    }
    if (!open) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(a+1, filtered.length-1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a-1, 0)); }
    else if (e.key === 'Escape') setOpen(false);
  };

  const onBlur = () => {
    // small delay so mousedown on suggestion fires first
    setTimeout(() => {
      if (value.trim()) pick(value.trim());
      setOpen(false);
    }, 150);
  };

  return (
    <InputWrap ref={ref}>
      <BaseInput
        value={value}
        onChange={e => { onChange(e.target.value); }}
        onKeyDown={onKey}
        onBlur={onBlur}
        onFocus={() => filtered.length > 0 && setOpen(true)}
        placeholder={placeholder}
        disabled={disabled}
        maxLength={200}
        autoComplete="off"
        borderColor={accentBorder}
        focusColor={focusColor}
        glowColor={glowColor}
      />
      {open && (
        <SuggestBox accentBorder={accentBorder}>
          {filtered.map((s, i) => (
            <SuggestItem key={s} active={i === active} onMouseDown={() => pick(s)}>
              💊 {s}
            </SuggestItem>
          ))}
        </SuggestBox>
      )}
    </InputWrap>
  );
}

// ── Medicine slot (selected medicine card) ────────────────────────────────────

const SlotCard = styled.div`
  flex: 1;
  background: ${CLR.input};
  border: 1px solid ${p => p.borderColor || CLR.purpleBorder};
  border-radius: 14px;
  padding: 12px 16px;
  min-width: 0;
  position: relative;
`;

const SlotName = styled.div`
  font-size: 0.92rem;
  font-weight: 600;
  color: ${CLR.text};
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const SlotActions = styled.div`
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
`;

// ── ExpandSection ─────────────────────────────────────────────────────────────

const ExpandToggle = styled.button`
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 11px 16px;
  background: rgba(99,102,241,0.05);
  border: 1px solid ${CLR.border};
  border-radius: 11px;
  color: #a5b4fc;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  margin-top: 10px;
  text-align: left;
  transition: background 0.2s;
  &:hover { background: rgba(99,102,241,0.1); }
`;

const ExpandBody = styled.div`
  padding: 16px;
  background: rgba(2,6,23,0.4);
  border: 1px solid ${CLR.border};
  border-top: none;
  border-radius: 0 0 11px 11px;
  animation: ${fadeInUp} 0.25s ease forwards;
`;

function Expandable({ label, children }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <ExpandToggle onClick={() => setOpen(o => !o)}>
        <span style={{ transform: open ? 'rotate(90deg)' : 'none', display:'inline-block', transition:'0.2s' }}>▶</span>
        {label}
      </ExpandToggle>
      {open && <ExpandBody>{children}</ExpandBody>}
    </>
  );
}

// ── Ask panel ─────────────────────────────────────────────────────────────────

const ASK_SAMPLES = [
  { label: 'Paracetamol',          q: 'What are the uses and side effects of Paracetamol 500mg?' },
  { label: 'Ibuprofen alternatives', q: 'What are alternatives to Ibuprofen 400mg?' },
  { label: 'Azithromycin info',    q: 'Full details on Azithromycin 500mg tablet' },
  { label: 'Metformin precautions', q: 'Precautions to take with Metformin 500mg?' },
];

const MODE_LABEL = { info: '💊 Medicine Info', comparison: '⚖️ Comparison', alternatives: '🔄 Alternatives' };

function AskPanel() {
  const [query, setQuery]   = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState(null);
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const doAsk = useCallback(async (q) => {
    const text = (q || query).trim();
    if (!text) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await axios.post('/api/medicine', { query: text });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to get response.');
    } finally { setLoading(false); }
  }, [query]);

  return (
    <>
      <Card border={CLR.greenBorder}>
        <Label>Ask about any medicine</Label>
        <div style={{ display:'flex', gap:10, alignItems:'stretch', flexWrap:'wrap' }}>
          <div style={{ flex:1, minWidth:200 }}>
            <BaseInput
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doAsk()}
              placeholder="e.g. Side effects of Metformin 500mg?"
              disabled={loading}
              maxLength={500}
            />
          </div>
          <Btn onClick={() => doAsk()} disabled={loading || !query.trim()}>
            {loading
              ? <><SpinnerIcon /> Asking…</>
              : '💊 Ask'}
          </Btn>
        </div>
        <Chips>
          <span style={{ fontSize:'0.72rem', color:CLR.muted }}>Try:</span>
          {ASK_SAMPLES.map(s => (
            <Chip key={s.label} onClick={() => { setQuery(s.q); doAsk(s.q); }} disabled={loading}>
              {s.label}
            </Chip>
          ))}
        </Chips>
      </Card>

      {loading && <LoadingDots><span/><span/><span/></LoadingDots>}

      {!loading && error && (
        <ErrorBox>
          <span style={{ fontSize:'1.3rem' }}>⚠️</span>
          <div style={{ flex:1 }}>
            <div style={{ color:'#fca5a5', fontWeight:600, marginBottom:8 }}>Something went wrong</div>
            <div style={{ color:'#94a3b8', fontSize:'0.85rem', marginBottom:12 }}>{error}</div>
            <GhostBtn borderColor="rgba(239,68,68,0.3)" color="#fca5a5" hoverBg="rgba(239,68,68,0.08)" hoverColor="#fca5a5" hoverBorder="rgba(239,68,68,0.4)" onClick={() => doAsk()}>
              ↻ Retry
            </GhostBtn>
          </div>
        </ErrorBox>
      )}

      {!loading && result && (
        <AnimatedCard border={CLR.greenBorder}>
          <ModeBadge>{MODE_LABEL[result.mode] || '💊 Result'}</ModeBadge>
          <MarkdownBlock dangerouslySetInnerHTML={{ __html: renderMarkdown(result.answer) }} />
          <Expandable label="Sources & disclaimer">
            <Disclaimer style={{ marginTop:0 }}>⚕️ {result.disclaimer}</Disclaimer>
          </Expandable>
        </AnimatedCard>
      )}
    </>
  );
}

// ── Compare panel ─────────────────────────────────────────────────────────────

const COMPARE_SAMPLES = [
  { a:'Dolo 650',          b:'Calpol 500' },
  { a:'Ibuprofen 400mg',   b:'Paracetamol 500mg' },
  { a:'Amoxicillin 500mg', b:'Azithromycin 500mg' },
  { a:'Pan 40',            b:'Omeprazole 20mg' },
];

// Rows shown in the three-column layout
const COMPARE_ROWS = [
  { key: 'uses',                 label: 'Uses' },
  { key: 'common_dosage',        label: 'Common Dosage' },
  { key: 'mechanism',            label: 'Mechanism of Action' },
  { key: 'side_effects',         label: 'Common Side Effects' },
  { key: 'suitable_for',         label: 'Suitable For' },
  { key: 'active_ingredients',   label: 'Active Ingredients' },
  { key: 'strength',             label: 'Strength' },
  { key: 'dosage_form',          label: 'Dosage Form' },
  { key: 'manufacturer',         label: 'Manufacturer' },
  { key: 'mrp',                  label: 'MRP (approx)' },
  { key: 'drug_interactions',    label: 'Drug Interactions' },
  { key: 'warnings',             label: 'Warnings' },
  { key: 'prescription_required',label: 'Prescription Required' },
];

// ── Three-column comparison layout styled components ──────────────────────────

const CompareGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 160px 1fr;
  gap: 0;
  margin-bottom: 20px;
  animation: ${fadeInUp} 0.4s ease forwards;

  @media(max-width: 680px) {
    grid-template-columns: 1fr;
  }
`;

const MedHeader = styled.div`
  border-radius: ${p => p.side === 'a' ? '16px 0 0 0' : '0 16px 0 0'};
  background: ${p => p.side === 'a'
    ? 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05))'
    : 'linear-gradient(135deg, rgba(139,92,246,0.15), rgba(139,92,246,0.05))'};
  border: 1px solid ${p => p.side === 'a' ? CLR.greenBorder : CLR.purpleBorder};
  border-bottom: none;
  padding: 22px 20px 18px;

  @media(max-width: 680px) {
    border-radius: ${p => p.side === 'a' ? '16px 16px 0 0' : '0'};
    border-bottom: ${p => p.side === 'a' ? 'none' : `1px solid ${CLR.purpleBorder}`};
  }
`;

const SpineHeader = styled.div`
  background: rgba(15,23,42,0.9);
  border-top: 1px solid ${CLR.border};
  border-bottom: none;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px 8px;

  @media(max-width: 680px) { display: none; }
`;

const ProductLabel = styled.div`
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: ${p => p.color};
  background: ${p => p.bg};
  border: 1px solid ${p => p.borderColor};
  border-radius: 100px;
  padding: 2px 10px;
  display: inline-block;
  margin-bottom: 10px;
`;

const MedName = styled.div`
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.3rem;
  font-weight: 700;
  color: ${CLR.text};
  line-height: 1.2;
  margin-bottom: 4px;
`;

const MedBrand = styled.div`
  font-size: 0.82rem;
  color: ${CLR.sub};
`;

// A single comparison row: left cell | spine pill | right cell
const RowLeft = styled.div`
  background: rgba(17,24,39,0.7);
  border-left: 1px solid ${CLR.greenBorder};
  border-right: none;
  border-top: 1px solid rgba(16,185,129,0.08);
  border-bottom: none;
  padding: 16px 20px;
  position: relative;

  /* dotted connector line on right edge */
  &::after {
    content: '';
    position: absolute;
    right: 0;
    top: 50%;
    width: 100%;
    height: 1px;
    background: repeating-linear-gradient(
      90deg,
      rgba(16,185,129,0.3) 0px,
      rgba(16,185,129,0.3) 4px,
      transparent 4px,
      transparent 10px
    );
    pointer-events: none;
    z-index: 0;
  }

  @media(max-width: 680px) {
    border: 1px solid ${CLR.greenBorder};
    border-top: none;
    &::after { display: none; }
  }
`;

const RowRight = styled.div`
  background: rgba(17,24,39,0.7);
  border-right: 1px solid ${CLR.purpleBorder};
  border-left: none;
  border-top: 1px solid rgba(139,92,246,0.08);
  border-bottom: none;
  padding: 16px 20px;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    width: 100%;
    height: 1px;
    background: repeating-linear-gradient(
      90deg,
      transparent 0px,
      transparent 6px,
      rgba(139,92,246,0.3) 6px,
      rgba(139,92,246,0.3) 10px
    );
    pointer-events: none;
    z-index: 0;
  }

  @media(max-width: 680px) {
    border: 1px solid ${CLR.purpleBorder};
    border-top: none;
    &::before { display: none; }
  }
`;

const RowSpine = styled.div`
  background: rgba(15,23,42,0.95);
  border-top: 1px solid ${CLR.border};
  border-left: 1px solid ${CLR.border};
  border-right: 1px solid ${CLR.border};
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 6px;
  z-index: 1;

  @media(max-width: 680px) { display: none; }
`;

const SpinePill = styled.div`
  background: rgba(30,41,59,0.95);
  border: 1px solid ${CLR.border};
  border-radius: 100px;
  padding: 6px 12px;
  font-size: 0.7rem;
  font-weight: 700;
  color: ${CLR.sub};
  text-align: center;
  letter-spacing: 0.04em;
  line-height: 1.3;
  white-space: nowrap;
  z-index: 2;
`;

// Last row gets bottom border-radius
const RowLeftLast = styled(RowLeft)`
  border-bottom: 1px solid ${CLR.greenBorder};
  border-radius: 0 0 0 16px;
  @media(max-width: 680px) { border-radius: 0; }
`;

const RowRightLast = styled(RowRight)`
  border-bottom: 1px solid ${CLR.purpleBorder};
  border-radius: 0 0 16px 0;
  @media(max-width: 680px) { border-radius: 0 0 16px 16px; }
`;

const RowSpineLast = styled(RowSpine)`
  border-bottom: 1px solid ${CLR.border};
  border-radius: 0 0 0 0;
`;

const CellLabel = styled.div`
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: ${p => p.color || CLR.green};
  margin-bottom: 5px;
`;

const CellValue = styled.div`
  font-size: 0.85rem;
  color: ${p => p.muted ? CLR.muted : '#cbd5e1'};
  line-height: 1.6;
  position: relative;
  z-index: 1;
`;

const NA = () => <CellValue muted>Data not available</CellValue>;

const KeyDiffBox = styled.div`
  background: rgba(99,102,241,0.06);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 16px;
  animation: ${fadeInUp} 0.4s ease forwards;
`;

const SubstBox = styled.div`
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 16px;
  border: 1px solid ${p => p.borderColor || 'rgba(99,102,241,0.2)'};
  animation: ${fadeInUp} 0.4s ease forwards;
`;

const SubstHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 22px;
  background: ${p => p.bg || 'rgba(99,102,241,0.08)'};
  border-bottom: 1px solid ${p => p.borderColor || 'rgba(99,102,241,0.15)'};
`;

const VerdictBadge = styled.span`
  padding: 3px 14px;
  border-radius: 100px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: ${p => p.bg};
  color: ${p => p.color};
  border: 1px solid ${p => p.borderColor};
  white-space: nowrap;
`;

const SubstConditions = styled.div`
  padding: 14px 22px;
  background: rgba(15,23,42,0.5);
  border-top: 1px solid rgba(99,102,241,0.1);
  font-size: 0.83rem;
  color: #cbd5e1;
  line-height: 1.6;
`;

const SubstCaution = styled.div`
  padding: 12px 22px;
  background: rgba(245,158,11,0.05);
  border-top: 1px solid rgba(245,158,11,0.15);
  font-size: 0.8rem;
  color: #fbbf24;
  line-height: 1.6;
`;

// ── Skeleton for three-column layout ─────────────────────────────────────────

const shimmerStyleLocal = css`
  background: linear-gradient(90deg,rgba(30,41,59,0.8) 25%,rgba(51,65,85,0.6) 50%,rgba(30,41,59,0.8) 75%);
  background-size:800px 100%;
  animation:${shimmer} 1.4s ease-in-out infinite;
`;

const SkeletonLine = styled.div`
  ${shimmerStyleLocal}
  height:${p=>p.h||'13px'};
  width:${p=>p.w||'100%'};
  border-radius:6px;
  margin-bottom:${p=>p.mb||'9px'};
`;

function CompareSkeleton() {
  return (
    <div style={{ display:'grid', gridTemplateColumns:'1fr 160px 1fr', gap:0, marginBottom:20 }}>
      {[0,1,2].map(col => (
        <div key={col} style={{
          background: CLR.card,
          border:`1px solid ${CLR.border}`,
          borderRadius: col===0?'16px 0 0 16px': col===2?'0 16px 16px 0':'0',
          padding:'22px 20px'
        }}>
          <SkeletonLine h="10px" w="60px" mb="14px" />
          <SkeletonLine h="22px" w="80%" mb="8px" />
          <SkeletonLine h="10px" w="50%" mb="24px" />
          {[90,70,85,60,80,75].map((w,i)=>(
            <SkeletonLine key={i} w={`${w}%`} mb="10px" />
          ))}
        </div>
      ))}
    </div>
  );
}

function ComparePanel() {
  const [medA, setMedA]       = useState('');
  const [medB, setMedB]       = useState('');
  const [lockedA, setLockedA] = useState('');
  const [lockedB, setLockedB] = useState('');
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const bothLocked = lockedA && lockedB;

  const doCompare = useCallback(async (a, b) => {
    const mA = (a || lockedA).trim();
    const mB = (b || lockedB).trim();
    if (!mA || !mB) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await axios.post('/api/medicine/compare', { medicine_a: mA, medicine_b: mB });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Comparison failed. Please try again.');
    } finally { setLoading(false); }
  }, [lockedA, lockedB]);

  const selectA = s => { setMedA(s); setLockedA(s); };
  const selectB = s => { setMedB(s); setLockedB(s); };

  const swap = () => {
    const [tA, tB] = [lockedA, lockedB];
    setLockedA(tB); setMedA(tB);
    setLockedB(tA); setMedB(tA);
    setResult(null);
  };

  const clear = () => {
    setMedA(''); setMedB(''); setLockedA(''); setLockedB('');
    setResult(null); setError(null);
  };

  // Render substitutability section
  const renderSubstitutability = (sub, nameA, nameB) => {
    if (!sub) return null;

    const verdictMap = {
      yes:     { label: 'Yes, can be replaced',     bg: 'rgba(16,185,129,0.15)',  color: '#34d399', borderColor: 'rgba(16,185,129,0.3)',  headerBg: 'rgba(16,185,129,0.07)',  headerBorder: 'rgba(16,185,129,0.2)'  },
      partial: { label: 'Partially — with conditions', bg: 'rgba(245,158,11,0.15)', color: '#fbbf24', borderColor: 'rgba(245,158,11,0.3)', headerBg: 'rgba(245,158,11,0.07)', headerBorder: 'rgba(245,158,11,0.2)' },
      no:      { label: 'No, cannot be replaced',   bg: 'rgba(239,68,68,0.15)',   color: '#fca5a5', borderColor: 'rgba(239,68,68,0.3)',   headerBg: 'rgba(239,68,68,0.07)',   headerBorder: 'rgba(239,68,68,0.2)'  },
    };

    const v = verdictMap[sub.verdict] || verdictMap.partial;

    return (
      <SubstBox borderColor={v.borderColor}>
        {/* Header */}
        <SubstHeader bg={v.headerBg} borderColor={v.headerBorder}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: CLR.sub, marginBottom: 8 }}>
              Can <strong style={{ color: CLR.text }}>{nameA}</strong> be replaced by <strong style={{ color: CLR.text }}>{nameB}</strong>?
            </div>
            <VerdictBadge bg={v.bg} color={v.color} borderColor={v.borderColor}>
              {v.label}
            </VerdictBadge>
            {sub.summary && (
              <div style={{ marginTop: 10, fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.65 }}>
                {sub.summary}
              </div>
            )}
          </div>
        </SubstHeader>

        {/* Reason */}
        {sub.reason && (
          <SubstConditions>
            <span style={{ fontWeight: 600, color: '#a5b4fc' }}>Why: </span>
            {sub.reason}
          </SubstConditions>
        )}

        {/* Conditions */}
        {sub.conditions && (
          <SubstConditions style={{ borderTop: '1px solid rgba(99,102,241,0.1)' }}>
            <span style={{ fontWeight: 600, color: '#a5b4fc' }}>Conditions: </span>
            {sub.conditions}
          </SubstConditions>
        )}

        {/* Caution */}
        {sub.caution && (
          <SubstCaution>
            ⚠️ <span style={{ fontWeight: 600 }}>Caution: </span>{sub.caution}
          </SubstCaution>
        )}
      </SubstBox>
    );
  };

  // Render the three-column comparison table from structured data
  const renderStructured = (data) => {
    const A = data.med_a || {};
    const B = data.med_b || {};

    return (
      <>
        <CompareGrid>
          {/* Header row */}
          <MedHeader side="a">
            <ProductLabel color={CLR.green} bg={CLR.greenDim} borderColor={CLR.greenBorder}>
              Product A
            </ProductLabel>
            <MedName>{A.generic_name || lockedA}</MedName>
            {A.brand_name && A.brand_name !== A.generic_name && (
              <MedBrand>{A.brand_name}</MedBrand>
            )}
          </MedHeader>

          <SpineHeader>
            <SpinePill>vs</SpinePill>
          </SpineHeader>

          <MedHeader side="b">
            <ProductLabel color="#a78bfa" bg={CLR.purpleDim} borderColor={CLR.purpleBorder}>
              Product B
            </ProductLabel>
            <MedName>{B.generic_name || lockedB}</MedName>
            {B.brand_name && B.brand_name !== B.generic_name && (
              <MedBrand>{B.brand_name}</MedBrand>
            )}
          </MedHeader>

          {/* Data rows */}
          {COMPARE_ROWS.map((row, idx) => {
            const isLast = idx === COMPARE_ROWS.length - 1;
            const Left  = isLast ? RowLeftLast  : RowLeft;
            const Right = isLast ? RowRightLast : RowRight;
            const Spine = isLast ? RowSpineLast : RowSpine;
            const aVal = A[row.key];
            const bVal = B[row.key];

            return [
              <Left key={`a-${row.key}`}>
                <CellLabel color={CLR.green}>{row.label}</CellLabel>
                {aVal && aVal !== 'Data not available'
                  ? <CellValue>{aVal}</CellValue>
                  : <NA />}
              </Left>,

              <Spine key={`s-${row.key}`}>
                <SpinePill>{row.label}</SpinePill>
              </Spine>,

              <Right key={`b-${row.key}`}>
                <CellLabel color="#a78bfa">{row.label}</CellLabel>
                {bVal && bVal !== 'Data not available'
                  ? <CellValue>{bVal}</CellValue>
                  : <NA />}
              </Right>,
            ];
          })}
        </CompareGrid>

        {/* Key differences */}
        {data.key_differences && (
          <KeyDiffBox>
            <div style={{ fontSize:'0.72rem', fontWeight:700, letterSpacing:'0.1em', textTransform:'uppercase', color:'#a5b4fc', marginBottom:10 }}>
              Key Differences
            </div>
            <div style={{ fontSize:'0.88rem', color:'#cbd5e1', lineHeight:1.7 }}>
              {data.key_differences}
            </div>
          </KeyDiffBox>
        )}

        {/* Substitutability */}
        {renderSubstitutability(data.substitutability, A.generic_name || lockedA, B.generic_name || lockedB)}

        <Disclaimer>
          ⚕️ {data.disclaimer || 'This information is for educational purposes only. Always consult a qualified healthcare professional before making any medical decisions.'}
        </Disclaimer>
      </>
    );
  };

  return (
    <>
      {/* Input card */}
      <Card border={CLR.purpleBorder}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14 }}>
          <Label color="#a78bfa" style={{ margin:0 }}>Select two medicines to compare</Label>
          {(lockedA || lockedB) && (
            <GhostBtn sm onClick={clear} borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple}>
              ✕ Clear all
            </GhostBtn>
          )}
        </div>

        <div style={{ display:'flex', gap:10, alignItems:'flex-start', flexWrap:'wrap', marginBottom:14 }}>
          {/* Slot A */}
          <div style={{ flex:1, minWidth:200 }}>
            {lockedA ? (
              <SlotCard borderColor="rgba(16,185,129,0.35)">
                <div style={{ fontSize:'0.65rem', color:CLR.green, textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:3 }}>Medicine A</div>
                <SlotName>{lockedA}</SlotName>
                <SlotActions>
                  <GhostBtn sm borderColor={CLR.greenBorder} color={CLR.green} hoverBg={CLR.greenDim} hoverColor={CLR.green} hoverBorder={CLR.green}
                    onClick={() => { setLockedA(''); setMedA(''); setResult(null); }}>
                    ✎ Replace
                  </GhostBtn>
                </SlotActions>
              </SlotCard>
            ) : (
              <AutoInput value={medA} onChange={setMedA} onSelect={selectA}
                placeholder="Medicine A — e.g. Dolo 650" disabled={loading}
                accentBorder="rgba(16,185,129,0.3)" focusColor={CLR.green} glowColor="rgba(16,185,129,0.1)" />
            )}
          </div>

          {/* VS / Swap */}
          <div style={{ display:'flex', alignItems:'center', justifyContent:'center', paddingTop: lockedA || lockedB ? 14 : 10 }}>
            {bothLocked
              ? <GhostBtn onClick={swap} disabled={loading} borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#c4b5fd" hoverBorder={CLR.purple}>⇄ Swap</GhostBtn>
              : <span style={{ color:CLR.muted, fontSize:'0.72rem', fontWeight:700, letterSpacing:'0.08em', padding:'0 4px' }}>VS</span>
            }
          </div>

          {/* Slot B */}
          <div style={{ flex:1, minWidth:200 }}>
            {lockedB ? (
              <SlotCard borderColor="rgba(139,92,246,0.35)">
                <div style={{ fontSize:'0.65rem', color:'#a78bfa', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:3 }}>Medicine B</div>
                <SlotName>{lockedB}</SlotName>
                <SlotActions>
                  <GhostBtn sm borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple}
                    onClick={() => { setLockedB(''); setMedB(''); setResult(null); }}>
                    ✎ Replace
                  </GhostBtn>
                </SlotActions>
              </SlotCard>
            ) : (
              <AutoInput value={medB} onChange={setMedB} onSelect={selectB}
                placeholder="Medicine B — e.g. Calpol 500" disabled={loading}
                accentBorder={CLR.purpleBorder} focusColor={CLR.purple} glowColor="rgba(139,92,246,0.1)" />
            )}
          </div>
        </div>

        {/* Actions row */}
        <div style={{ display:'flex', gap:10, alignItems:'center', flexWrap:'wrap' }}>
          <Btn bg="linear-gradient(135deg,#7c3aed,#8b5cf6)" onClick={() => doCompare()}
            disabled={loading || !bothLocked} style={{ minWidth:140 }}>
            {loading ? <><SpinnerIcon /> Comparing…</> : 'Compare'}
          </Btn>
          {result && !loading && (
            <GhostBtn borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple}
              onClick={() => doCompare()} disabled={loading}>↻ Refresh</GhostBtn>
          )}
          {!bothLocked && (
            <span style={{ color:CLR.muted, fontSize:'0.78rem' }}>
              {!lockedA && !lockedB ? 'Select both medicines to compare' : !lockedA ? 'Select Medicine A' : 'Select Medicine B'}
            </span>
          )}
        </div>

        <Chips>
          <span style={{ fontSize:'0.72rem', color:CLR.muted }}>Quick compare:</span>
          {COMPARE_SAMPLES.map(s => (
            <Chip key={s.a} bg={CLR.purpleDim} borderColor={CLR.purpleBorder} color="#a78bfa"
              onClick={() => { selectA(s.a); selectB(s.b); doCompare(s.a, s.b); }} disabled={loading}>
              {s.a} vs {s.b}
            </Chip>
          ))}
        </Chips>
      </Card>

      {loading && <CompareSkeleton />}

      {!loading && error && (
        <ErrorBox>
          <div style={{ flex:1 }}>
            <div style={{ color:'#fca5a5', fontWeight:600, marginBottom:8 }}>Comparison failed</div>
            <div style={{ color:CLR.sub, fontSize:'0.85rem', marginBottom:12 }}>{error}</div>
            <GhostBtn borderColor="rgba(239,68,68,0.3)" color="#fca5a5" hoverBg="rgba(239,68,68,0.08)" hoverColor="#fca5a5" hoverBorder="rgba(239,68,68,0.4)"
              onClick={() => doCompare()} disabled={!bothLocked}>↻ Retry</GhostBtn>
          </div>
        </ErrorBox>
      )}

      {!loading && !error && result && (
        <div>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16, flexWrap:'wrap', gap:8 }}>
            <span style={{ fontSize:'0.72rem', color:CLR.sub, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.08em' }}>
              Comparison Result
            </span>
            <div style={{ display:'flex', gap:8 }}>
              <GhostBtn sm borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple}
                onClick={swap}>⇄ Swap</GhostBtn>
              <GhostBtn sm borderColor={CLR.border} color={CLR.sub} onClick={clear}>✕ Clear</GhostBtn>
            </div>
          </div>
          {renderStructured(result)}
        </div>
      )}

      {!loading && !error && !result && bothLocked && (
        <Card border={CLR.border} style={{ textAlign:'center', padding:'28px 24px' }}>
          <div style={{ color:CLR.sub, fontSize:'0.9rem' }}>
            Ready to compare <strong style={{ color:CLR.text }}>{lockedA}</strong> and <strong style={{ color:CLR.text }}>{lockedB}</strong>
          </div>
          <div style={{ color:CLR.muted, fontSize:'0.8rem', marginTop:6 }}>Hit Compare to see the full breakdown</div>
        </Card>
      )}
    </>
  );
}

// ── SubTab bar ────────────────────────────────────────────────────────────────

const SubTabBar = styled.div`
  display: flex;
  gap: 6px;
  margin-bottom: 24px;
  align-items: center;
`;

const SubTab = styled.button`
  padding: 8px 20px;
  border-radius: 10px;
  border: 1px solid ${p => p.$active ? CLR.purpleBorder : CLR.border};
  background: ${p => p.$active ? CLR.purpleDim : 'transparent'};
  color: ${p => p.$active ? '#a78bfa' : CLR.muted};
  font-size: 0.83rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: ${CLR.purpleBorder}; color: #a78bfa; background: ${CLR.purpleDim}; }
`;

// ── Root export ───────────────────────────────────────────────────────────────

function MedicineAssistant({ initialTab }) {
  const [tab, setTab] = useState(initialTab || 'ask');

  return (
    <Wrapper>
      <SubTabBar>
        <SubTab $active={tab === 'ask'} onClick={() => setTab('ask')}>💊 Ask</SubTab>
        <SubTab $active={tab === 'compare'} onClick={() => setTab('compare')}>⚖️ Compare</SubTab>
      </SubTabBar>
      {tab === 'ask'     && <AskPanel />}
      {tab === 'compare' && <ComparePanel />}
    </Wrapper>
  );
}

export default MedicineAssistant;
