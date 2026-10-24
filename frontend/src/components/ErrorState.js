import React from 'react';
import styled, { keyframes } from 'styled-components';

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
`;

const Wrapper = styled.div`
  background: rgba(239,68,68,0.06);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 16px;
  padding: 28px 32px;
  text-align: center;
  animation: ${fadeIn} 0.4s ease;
`;

const Icon = styled.div`
  font-size: 2.5rem;
  margin-bottom: 14px;
`;

const Title = styled.div`
  font-size: 1rem;
  font-weight: 600;
  color: #fca5a5;
  margin-bottom: 8px;
`;

const Message = styled.div`
  font-size: 0.88rem;
  color: #f87171;
  opacity: 0.7;
  margin-bottom: 20px;
  font-family: 'Space Grotesk', monospace;
  background: rgba(239,68,68,0.08);
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid rgba(239,68,68,0.15);
  text-align: left;
  line-height: 1.6;
`;

const RetryBtn = styled.button`
  background: rgba(239,68,68,0.12);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 10px;
  padding: 10px 24px;
  color: #fca5a5;
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(239,68,68,0.2);
    border-color: rgba(239,68,68,0.5);
  }
`;

function ErrorState({ message, onRetry }) {
  return (
    <Wrapper>
      <Icon>⚠️</Icon>
      <Title>Something went wrong</Title>
      <Message>{message}</Message>
      <RetryBtn onClick={onRetry}>↺ Try Again</RetryBtn>
    </Wrapper>
  );
}

export default ErrorState;
