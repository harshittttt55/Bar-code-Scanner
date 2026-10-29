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

// ── Skeleton loader ───────────────────────────────────────────────────────────

const shimmerStyle = css`
  background: linear-gradient(90deg, rgba(30,41,59,0.8) 25%, rgba(51,65,85,0.6) 50%, rgba(30,41,59,0.8) 75%);
  background-size: 800px 100%;
  animation: ${shimmer} 1.4s ease-in-out infinite;
`;

const SkeletonLine = styled.div`
  ${shimmerStyle}
  height: ${p => p.h || '14px'};
  width: ${p => p.w || '100%'};
  border-radius: 6px;
  margin-bottom: ${p => p.mb || '10px'};
`;

const SkeletonBlock = styled.div`
  background: ${CLR.card};
  border: 1px solid ${CLR.border};
  border-radius: 16px;
  padding: 22px 26px;
  margin-bottom: 14px;
`;

function CompareSkeleton() {
  return (
    <>
      <SkeletonBlock>
        <SkeletonLine h="10px" w="120px" mb="18px" />
        {[100, 80, 90, 70, 85, 75, 95].map((w, i) => (
          <SkeletonLine key={i} w={`${w}%`} mb="10px" />
        ))}
      </SkeletonBlock>
      <SkeletonBlock>
        <SkeletonLine h="10px" w="100px" mb="14px" />
        <SkeletonLine w="88%" />
        <SkeletonLine w="70%" />
      </SkeletonBlock>
    </>
  );
}

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
    if (!open) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(a+1, filtered.length-1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a-1, 0)); }
    else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); pick(filtered[active]); }
    else if (e.key === 'Escape') setOpen(false);
  };

  return (
    <InputWrap ref={ref}>
      <BaseInput
        value={value}
        onChange={e => { onChange(e.target.value); }}
        onKeyDown={onKey}
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

function ComparePanel() {
  const [medA, setMedA]     = useState('');
  const [medB, setMedB]     = useState('');
  const [lockedA, setLockedA] = useState('');
  const [lockedB, setLockedB] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState(null);

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
    const tmpA = lockedA, tmpB = lockedB;
    setLockedA(tmpB); setMedA(tmpB);
    setLockedB(tmpA); setMedB(tmpA);
    setResult(null);
  };

  const clear = () => {
    setMedA(''); setMedB(''); setLockedA(''); setLockedB('');
    setResult(null); setError(null);
  };

  const replaceA = () => { setLockedA(''); setMedA(''); setResult(null); };
  const replaceB = () => { setLockedB(''); setMedB(''); setResult(null); };

  return (
    <>
      {/* Input area */}
      <Card border={CLR.purpleBorder}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14 }}>
          <Label color="#a78bfa" style={{ margin:0 }}>Select two medicines to compare</Label>
          {(lockedA || lockedB) && (
            <GhostBtn sm onClick={clear} borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple}>
              ✕ Clear all
            </GhostBtn>
          )}
        </div>

        {/* Slots row */}
        <div style={{ display:'flex', gap:10, alignItems:'flex-start', flexWrap:'wrap', marginBottom:14 }}>
          {/* Slot A */}
          <div style={{ flex:1, minWidth:200 }}>
            {lockedA ? (
              <SlotCard borderColor="rgba(16,185,129,0.35)">
                <div style={{ fontSize:'0.65rem', color:CLR.green, textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:3 }}>Medicine A</div>
                <SlotName>{lockedA}</SlotName>
                <SlotActions>
                  <GhostBtn sm borderColor="rgba(16,185,129,0.25)" color={CLR.green} hoverBg={CLR.greenDim} hoverColor={CLR.green} hoverBorder={CLR.green} onClick={replaceA}>
                    ✎ Replace
                  </GhostBtn>
                </SlotActions>
              </SlotCard>
            ) : (
              <AutoInput
                value={medA}
                onChange={setMedA}
                onSelect={selectA}
                placeholder="Medicine A — e.g. Dolo 650"
                disabled={loading}
                accentBorder="rgba(16,185,129,0.3)"
                focusColor={CLR.green}
                glowColor="rgba(16,185,129,0.1)"
              />
            )}
          </div>

          {/* Swap/VS button */}
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:4, paddingTop: lockedA || lockedB ? 14 : 10 }}>
            {bothLocked ? (
              <GhostBtn
                onClick={swap}
                disabled={loading}
                borderColor={CLR.purpleBorder}
                color="#a78bfa"
                hoverBg={CLR.purpleDim}
                hoverColor="#c4b5fd"
                hoverBorder={CLR.purple}
                title="Swap medicines"
              >
                ⇄ Swap
              </GhostBtn>
            ) : (
              <span style={{ color:CLR.muted, fontSize:'0.72rem', fontWeight:700, letterSpacing:'0.08em', padding:'0 4px' }}>VS</span>
            )}
          </div>

          {/* Slot B */}
          <div style={{ flex:1, minWidth:200 }}>
            {lockedB ? (
              <SlotCard borderColor="rgba(139,92,246,0.35)">
                <div style={{ fontSize:'0.65rem', color:'#a78bfa', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:3 }}>Medicine B</div>
                <SlotName>{lockedB}</SlotName>
                <SlotActions>
                  <GhostBtn sm borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple} onClick={replaceB}>
                    ✎ Replace
                  </GhostBtn>
                </SlotActions>
              </SlotCard>
            ) : (
              <AutoInput
                value={medB}
                onChange={setMedB}
                onSelect={selectB}
                placeholder="Medicine B — e.g. Calpol 500"
                disabled={loading}
                accentBorder={CLR.purpleBorder}
                focusColor={CLR.purple}
                glowColor="rgba(139,92,246,0.1)"
              />
            )}
          </div>
        </div>

        {/* Compare button */}
        <div style={{ display:'flex', gap:10, alignItems:'center', flexWrap:'wrap' }}>
          <Btn
            bg="linear-gradient(135deg,#7c3aed,#8b5cf6)"
            onClick={() => doCompare()}
            disabled={loading || !bothLocked}
            style={{ minWidth:140 }}
          >
            {loading
              ? <><SpinnerIcon /> Comparing…</>
              : '⚖️ Compare'}
          </Btn>
          {result && !loading && (
            <GhostBtn borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple} onClick={() => doCompare()} disabled={loading}>
              ↻ Refresh
            </GhostBtn>
          )}
          {!bothLocked && (
            <span style={{ color:CLR.muted, fontSize:'0.78rem' }}>
              {!lockedA && !lockedB ? 'Select both medicines to compare' : !lockedA ? 'Select Medicine A' : 'Select Medicine B'}
            </span>
          )}
        </div>

        {/* Sample chips */}
        <Chips>
          <span style={{ fontSize:'0.72rem', color:CLR.muted }}>Quick compare:</span>
          {COMPARE_SAMPLES.map(s => (
            <Chip key={s.a} bg={CLR.purpleDim} borderColor={CLR.purpleBorder} color="#a78bfa"
              onClick={() => { selectA(s.a); selectB(s.b); doCompare(s.a, s.b); }}
              disabled={loading}
            >
              {s.a} vs {s.b}
            </Chip>
          ))}
        </Chips>
      </Card>

      {/* Skeleton while loading */}
      {loading && <CompareSkeleton />}

      {/* Error state */}
      {!loading && error && (
        <ErrorBox>
          <span style={{ fontSize:'1.3rem' }}>⚠️</span>
          <div style={{ flex:1 }}>
            <div style={{ color:'#fca5a5', fontWeight:600, marginBottom:8 }}>Comparison failed</div>
            <div style={{ color:'#94a3b8', fontSize:'0.85rem', marginBottom:12 }}>{error}</div>
            <GhostBtn borderColor="rgba(239,68,68,0.3)" color="#fca5a5" hoverBg="rgba(239,68,68,0.08)" hoverColor="#fca5a5" hoverBorder="rgba(239,68,68,0.4)" onClick={() => doCompare()} disabled={!bothLocked}>
              ↻ Retry
            </GhostBtn>
          </div>
        </ErrorBox>
      )}

      {/* Result */}
      {!loading && !error && result && (
        <AnimatedCard border={CLR.purpleBorder}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:10, marginBottom:16 }}>
            <ModeBadge bg={CLR.purpleDim} borderColor={CLR.purpleBorder} color="#a78bfa">
              ⚖️ {lockedA} vs {lockedB}
            </ModeBadge>
            <div style={{ display:'flex', gap:8 }}>
              <GhostBtn sm borderColor={CLR.purpleBorder} color="#a78bfa" hoverBg={CLR.purpleDim} hoverColor="#a78bfa" hoverBorder={CLR.purple} onClick={swap}>
                ⇄ Swap & refresh
              </GhostBtn>
              <GhostBtn sm borderColor={CLR.border} color={CLR.sub} onClick={clear}>
                ✕ Clear
              </GhostBtn>
            </div>
          </div>

          <MarkdownBlock dangerouslySetInnerHTML={{ __html: renderMarkdown(result.answer) }} />

          <Expandable label="Disclaimer & sources">
            <Disclaimer style={{ marginTop:0 }}>⚕️ {result.disclaimer}</Disclaimer>
          </Expandable>
        </AnimatedCard>
      )}

      {/* Empty state — both selected but no result yet */}
      {!loading && !error && !result && bothLocked && (
        <Card border={CLR.border} style={{ textAlign:'center', padding:'32px 24px' }}>
          <div style={{ fontSize:'2rem', marginBottom:10 }}>⚖️</div>
          <div style={{ color:CLR.sub, fontSize:'0.9rem' }}>
            Ready to compare <strong style={{ color:CLR.text }}>{lockedA}</strong> and <strong style={{ color:CLR.text }}>{lockedB}</strong>
          </div>
          <div style={{ color:CLR.muted, fontSize:'0.8rem', marginTop:6 }}>Hit Compare to see the detailed breakdown</div>
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
