import React, { useRef, useEffect } from 'react';
import styled, { keyframes } from 'styled-components';

const shimmer = keyframes`
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
`;

const scanLine = keyframes`
  0% { top: 0; opacity: 1; }
  100% { top: 100%; opacity: 0; }
`;

const InputWrapper = styled.div`
  background: rgba(17, 24, 39, 0.8);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 20px;
  padding: 28px 32px;
  margin-bottom: 32px;
  backdrop-filter: blur(12px);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
  position: relative;
  overflow: hidden;

  &:focus-within {
    border-color: rgba(99, 102, 241, 0.5);
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.1), 0 8px 32px rgba(99, 102, 241, 0.08);
  }

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99,102,241,0.5), transparent);
    animation: ${shimmer} 3s infinite;
  }
`;

const Label = styled.label`
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #6366f1;
  margin-bottom: 12px;
`;

const InputRow = styled.div`
  display: flex;
  gap: 12px;
  align-items: stretch;

  @media (max-width: 480px) {
    flex-direction: column;
  }
`;

const StyledInput = styled.input`
  flex: 1;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 14px 18px;
  color: #f1f5f9;
  font-size: 1rem;
  font-family: 'Space Grotesk', monospace;
  letter-spacing: 0.06em;
  outline: none;
  transition: all 0.25s ease;
  width: 100%;

  &::placeholder {
    color: #334155;
    letter-spacing: 0.04em;
  }

  &:focus {
    border-color: rgba(99, 102, 241, 0.6);
    background: rgba(15, 23, 42, 0.9);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }
`;

const SearchButton = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border: none;
  border-radius: 12px;
  padding: 14px 28px;
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.1), transparent);
  }
`;

const QuickSamples = styled.div`
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
`;

const SampleLabel = styled.span`
  font-size: 0.75rem;
  color: #475569;
  font-weight: 500;
`;

const SampleChip = styled.button`
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.18);
  border-radius: 100px;
  padding: 4px 12px;
  font-size: 0.75rem;
  color: #818cf8;
  font-family: 'Space Grotesk', monospace;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(99, 102, 241, 0.18);
    border-color: rgba(99, 102, 241, 0.4);
    color: #a5b4fc;
  }
`;

const SAMPLE_BARCODES = [
  { code: '8901030861024', label: 'Maggi' },
  { code: '8901719101009', label: 'Parle-G' },
  { code: '012000001086', label: 'Pepsi' },
  { code: '038000138416', label: 'Kelloggs' },
];

function BarcodeInput({ barcode, setBarcode, onSearch, loading }) {
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') onSearch();
  };

  return (
    <InputWrapper>
      <Label>Enter Barcode Number</Label>
      <InputRow>
        <StyledInput
          ref={inputRef}
          type="text"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. 8901030861024"
          disabled={loading}
          maxLength={30}
          autoComplete="off"
        />
        <SearchButton onClick={() => onSearch()} disabled={loading || !barcode.trim()}>
          {loading ? (
            <>⏳ Scanning...</>
          ) : (
            <>🔍 Scan</>
          )}
        </SearchButton>
      </InputRow>

      <QuickSamples>
        <SampleLabel>Try:</SampleLabel>
        {SAMPLE_BARCODES.map((s) => (
          <SampleChip
            key={s.code}
            onClick={() => {
              setBarcode(s.code);
              onSearch(s.code);
            }}
            disabled={loading}
          >
            {s.label}
          </SampleChip>
        ))}
      </QuickSamples>
    </InputWrapper>
  );
}

export default BarcodeInput;
