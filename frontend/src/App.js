import React, { useState } from 'react';
import styled, { keyframes, createGlobalStyle } from 'styled-components';
import axios from 'axios';
import BarcodeInput from './components/BarcodeInput';
import ProductCard from './components/ProductCard';
import LoadingSpinner from './components/LoadingSpinner';
import EmptyState from './components/EmptyState';
import ErrorState from './components/ErrorState';
import MedicineAssistant from './components/MedicineAssistant';

const GlobalStyle = createGlobalStyle`
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', sans-serif;
    background: #0a0f1e;
    color: #f1f5f9;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
`;

const gradientShift = keyframes`
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
`;

const AppWrapper = styled.div`
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
`;

const Background = styled.div`
  position: fixed;
  inset: 0;
  z-index: 0;
  background: #0a0f1e;

  &::before {
    content: '';
    position: absolute;
    width: 600px; height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
    top: -200px; left: -100px;
    pointer-events: none;
  }
  &::after {
    content: '';
    position: absolute;
    width: 500px; height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(139,92,246,0.10) 0%, transparent 70%);
    bottom: -100px; right: -50px;
    pointer-events: none;
  }
`;

const GridLines = styled.div`
  position: fixed;
  inset: 0;
  z-index: 0;
  background-image:
    linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px);
  background-size: 50px 50px;
`;

const Container = styled.div`
  position: relative;
  z-index: 1;
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px 80px;
`;

const Header = styled.header`
  text-align: center;
  margin-bottom: 40px;
`;

const Icon = styled.div`
  font-size: 2.5rem;
  margin-bottom: 16px;
  animation: ${float} 3s ease-in-out infinite;
  user-select: none;
`;

const LogoBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.3);
  border-radius: 100px;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #a5b4fc;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 20px;

  .dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #6366f1;
    box-shadow: 0 0 8px #6366f1;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
`;

const Title = styled.h1`
  font-family: 'Space Grotesk', sans-serif;
  font-size: clamp(2.2rem, 5vw, 3.5rem);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 50%, #818cf8 100%);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: ${gradientShift} 4s ease infinite;
`;

const Subtitle = styled.p`
  color: #64748b;
  font-size: 1.05rem;
  max-width: 520px;
  margin: 0 auto;
  font-weight: 400;
`;

// ── Mode toggle ───────────────────────────────────────────────────────────────

const ToggleBar = styled.div`
  display: flex;
  gap: 8px;
  background: rgba(15,23,42,0.8);
  border: 1px solid rgba(99,102,241,0.15);
  border-radius: 14px;
  padding: 6px;
  margin-bottom: 32px;
  width: fit-content;
  margin-left: auto;
  margin-right: auto;
`;

const ToggleBtn = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  border-radius: 10px;
  border: none;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;

  ${({ active, mode }) => active ? `
    background: ${mode === 'medicine'
      ? 'linear-gradient(135deg, #059669, #10b981)'
      : 'linear-gradient(135deg, #6366f1, #8b5cf6)'};
    color: #fff;
    box-shadow: 0 4px 14px ${mode === 'medicine'
      ? 'rgba(16,185,129,0.3)'
      : 'rgba(99,102,241,0.3)'};
  ` : `
    background: transparent;
    color: #64748b;
    &:hover { color: #94a3b8; background: rgba(99,102,241,0.05); }
  `}
`;

// ── Medicine header ───────────────────────────────────────────────────────────

const MedTitle = styled(Title)`
  background: linear-gradient(135deg, #e2e8f0 0%, #6ee7b7 50%, #10b981 100%);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
`;

function App() {
  const [mode, setMode] = useState('barcode'); // 'barcode' | 'medicine'

  // Barcode state
  const [barcode, setBarcode] = useState('');
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (barcodeValue) => {
    const code = barcodeValue || barcode;
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setProduct(null);
    setSearched(true);
    try {
      const response = await axios.post('/api/product', { barcode: code.trim() });
      setProduct(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch product info. Please check your backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setBarcode('');
    setProduct(null);
    setError(null);
    setSearched(false);
  };

  const switchMode = (m) => {
    setMode(m);
    if (m === 'barcode') handleReset();
  };

  return (
    <>
      <GlobalStyle />
      <AppWrapper>
        <Background />
        <GridLines />
        <Container>
          <Header>
            <Icon>{mode === 'medicine' ? '💊' : '▦'}</Icon>
            <LogoBadge>
              <span className="dot" />
              Powered by Gemini AI
            </LogoBadge>
            {mode === 'medicine'
              ? <MedTitle>Medicine Assistant</MedTitle>
              : <Title>BarcodeAI Scanner</Title>
            }
            <Subtitle>
              {mode === 'medicine'
                ? 'Ask about any medicine — uses, side effects, comparisons, and alternatives'
                : 'Enter any product barcode and instantly get verified details'}
            </Subtitle>
          </Header>

          <ToggleBar>
            <ToggleBtn
              active={mode === 'barcode'}
              mode="barcode"
              onClick={() => switchMode('barcode')}
            >
              ▦ Barcode Scanner
            </ToggleBtn>
            <ToggleBtn
              active={mode === 'medicine'}
              mode="medicine"
              onClick={() => switchMode('medicine')}
            >
              💊 Medicine Assistant
            </ToggleBtn>
          </ToggleBar>

          {mode === 'barcode' && (
            <>
              <BarcodeInput
                barcode={barcode}
                setBarcode={setBarcode}
                onSearch={handleSearch}
                loading={loading}
              />

              {loading && <LoadingSpinner />}

              {!loading && error && (
                <ErrorState message={error} onRetry={() => handleSearch()} />
              )}

              {!loading && !error && product && product.found && (
                <ProductCard product={product} onReset={handleReset} />
              )}

              {!loading && !error && (!product || !product.found) && searched && (
                <EmptyState barcode={barcode} />
              )}
            </>
          )}

          {mode === 'medicine' && <MedicineAssistant />}
        </Container>
      </AppWrapper>
    </>
  );
}

export default App;
