import React from 'react';
import styled, { keyframes } from 'styled-components';

const float = keyframes`
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
`;

const Wrapper = styled.div`
  text-align: center;
  padding: 60px 20px;
  color: #475569;
`;

const Icon = styled.div`
  font-size: 3rem;
  margin-bottom: 16px;
  animation: ${float} 3s ease-in-out infinite;
`;

const Title = styled.div`
  font-size: 1.1rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
`;

const Sub = styled.div`
  font-size: 0.88rem;
  color: #334155;
`;

function EmptyState({ barcode }) {
  return (
    <Wrapper>
      <Icon>🔍</Icon>
      <Title>Product not found</Title>
      <Sub>
        {barcode
          ? <>Barcode <span style={{ color: '#818cf8', fontFamily: 'monospace' }}>{barcode}</span> wasn't found in our catalog or AI knowledge base.</>
          : 'Try a different barcode number'}
      </Sub>
      <Sub style={{ marginTop: 8 }}>Double-check the number or try scanning a different product.</Sub>
    </Wrapper>
  );
}

export default EmptyState;
