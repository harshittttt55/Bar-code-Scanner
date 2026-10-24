import React from 'react';
import styled, { keyframes } from 'styled-components';

const pulse = keyframes`
  0%, 100% { opacity: 0.4; transform: scaleY(0.6); }
  50% { opacity: 1; transform: scaleY(1); }
`;

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 24px;
`;

const Spinner = styled.div`
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 2px solid rgba(99,102,241,0.15);
  border-top-color: #6366f1;
  animation: ${spin} 0.8s linear infinite;
`;

const BarsWrapper = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
`;

const Bar = styled.div`
  width: 3px;
  height: ${props => props.h}px;
  background: #6366f1;
  border-radius: 2px;
  animation: ${pulse} 1.2s ease-in-out infinite;
  animation-delay: ${props => props.delay}s;
`;

const Text = styled.div`
  font-size: 0.95rem;
  color: #64748b;
  text-align: center;
  line-height: 1.6;
`;

const SubText = styled.div`
  font-size: 0.8rem;
  color: #334155;
  margin-top: 4px;
`;

const BARS = [
  { h: 14, d: 0 }, { h: 22, d: 0.15 }, { h: 30, d: 0.3 },
  { h: 22, d: 0.45 }, { h: 14, d: 0.6 }, { h: 22, d: 0.75 },
  { h: 30, d: 0.9 }, { h: 22, d: 1.05 }, { h: 14, d: 1.2 },
];

function LoadingSpinner() {
  return (
    <Wrapper>
      <Spinner />
      <BarsWrapper>
        {BARS.map((b, i) => (
          <Bar key={i} h={b.h} delay={b.d} />
        ))}
      </BarsWrapper>
      <Text>
        Scanning barcode with Gemini AI...
        <SubText>Fetching product details from the knowledge base</SubText>
      </Text>
    </Wrapper>
  );
}

export default LoadingSpinner;
