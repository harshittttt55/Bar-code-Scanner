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

function EmptyState() {
  return (
    <Wrapper>
      <Icon>🔍</Icon>
      <Title>No product found</Title>
      <Sub>Try a different barcode number</Sub>
    </Wrapper>
  );
}

export default EmptyState;
