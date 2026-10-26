
import React from 'react';
import styled, { keyframes } from 'styled-components';

const fadeInUp = keyframes`
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
`;

const Wrapper = styled.div`
  animation: ${fadeInUp} 0.5s ease forwards;
  color: #cbd5e1;
`;

const Header = styled.div`
  background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08));
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 20px;
  padding: 28px 32px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(99,102,241,0.1) 0%, transparent 70%);
    pointer-events: none;
  }
`;

const NotFoundBanner = styled.div`
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 12px;
  padding: 14px 20px;
  margin-bottom: 16px;
  color: #fca5a5;
  font-size: 0.88rem;
  line-height: 1.6;
`;

const ProductMeta = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 20px;

  @media (max-width: 650px) {
    flex-wrap: wrap;
  }
`;

const ProductEmoji = styled.div`
  font-size: 3rem;
  line-height: 1;
  flex-shrink: 0;
`;

const ProductInfo = styled.div`
  flex: 1;
  min-width: 0;
`;

const ProductName = styled.h2`
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.01em;
  line-height: 1.3;
  margin: 0 0 8px;
`;

const BrandBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 100px;
  padding: 4px 12px;
  font-size: 0.8rem;
  color: #a5b4fc;
  font-weight: 500;
  margin-bottom: 10px;
`;

const TagRow = styled.div`
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
`;

const Tag = styled.span`
  background: rgba(15,23,42,0.6);
  border: 1px solid rgba(99,102,241,0.15);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 500;
`;

const MrpBadge = styled.div`
  background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05));
  border: 1px solid rgba(16,185,129,0.3);
  border-radius: 12px;
  padding: 10px 16px;
  text-align: center;
  flex-shrink: 0;

  .label {
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #34d399;
    margin-bottom: 4px;
  }

  .price {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #10b981;
  }
`;

const MrpLoadingBadge = styled(MrpBadge)`
  background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(99,102,241,0.05));
  border-color: rgba(99,102,241,0.25);
  min-width: 80px;

  .label { color: #818cf8; }

  .price {
    font-size: 0.8rem;
    color: #818cf8;
    font-weight: 500;
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
`;

const InfoCard = styled.div`
  background: rgba(17,24,39,0.7);
  border: 1px solid rgba(99,102,241,0.12);
  border-radius: 16px;
  padding: 20px;
  min-width: 0;
  overflow-wrap: anywhere;
  transition: all 0.25s ease;

  &:hover {
    border-color: rgba(99,102,241,0.3);
    background: rgba(17,24,39,0.9);
  }
`;

const InfoCardIcon = styled.div`
  font-size: 1.4rem;
  margin-bottom: 10px;
`;

const InfoCardLabel = styled.div`
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #818cf8;
  margin-bottom: 8px;
`;

const InfoCardValue = styled.div`
  font-size: 0.9rem;
  color: #cbd5e1;
  line-height: 1.7;
  overflow-wrap: anywhere;
  word-break: break-word;

  a {
    color: #a5b4fc;
    text-decoration: underline;
  }
`;

const FullWidthCard = styled(InfoCard)`
  grid-column: 1 / -1;
`;

const BarcodeDisplay = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(17,24,39,0.7);
  border: 1px solid rgba(99,102,241,0.12);
  border-radius: 16px;
  padding: 16px 24px;
  margin-bottom: 16px;

  @media (max-width: 450px) {
    padding: 14px;
    flex-wrap: wrap;
  }
`;

const BarcodeText = styled.div`
  font-family: 'Space Grotesk', monospace;
  font-size: 1.1rem;
  letter-spacing: 0.08em;
  color: #818cf8;
  font-weight: 600;
  overflow-wrap: anywhere;
`;

const ResetButton = styled.button`
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 10px;
  padding: 8px 18px;
  color: #a5b4fc;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;

  &:hover {
    background: rgba(99,102,241,0.2);
    border-color: rgba(99,102,241,0.4);
  }
`;

const SectionTitle = styled.h3`
  color: #a5b4fc;
  font-size: 1rem;
  margin: 24px 0 12px;
`;

const Notice = styled.div`
  background: rgba(99,102,241,0.07);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 12px;
  padding: 14px 18px;
  margin: 12px 0 16px;
  line-height: 1.6;
  font-size: 0.85rem;
  overflow-wrap: anywhere;
`;

const ExpandSection = styled.details`
  background: rgba(17,24,39,0.65);
  border: 1px solid rgba(99,102,241,0.16);
  border-radius: 14px;
  margin: 12px 0;
  overflow: hidden;

  > summary {
    cursor: pointer;
    padding: 16px 18px;
    color: #a5b4fc;
    font-weight: 600;
  }

  > summary:hover {
    background: rgba(99,102,241,0.06);
  }
`;

const JsonBlock = styled.pre`
  padding: 16px;
  margin: 0;
  overflow: auto;
  max-height: 600px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  background: rgba(2,6,23,0.55);
  color: #cbd5e1;
  font-size: 0.8rem;
  line-height: 1.6;
`;

const getCategoryEmoji = (category) => {
  const c = String(category || '').toLowerCase();

  if (/food|snack|biscuit/.test(c)) return '🍪';
  if (/beverage|drink/.test(c)) return '🥤';
  if (/dairy|milk/.test(c)) return '🥛';
  if (/electronics/.test(c)) return '📱';
  if (/personal care|beauty|cosmetic|face wash/.test(c)) return '🧴';
  if (/health|medicine/.test(c)) return '💊';
  if (/noodle|pasta/.test(c)) return '🍜';
  if (/cereal|breakfast/.test(c)) return '🥣';

  return '📦';
};

const isEmpty = (value) =>
  value === null ||
  value === undefined ||
  value === '' ||
  (Array.isArray(value) && value.length === 0) ||
  (
    typeof value === 'object' &&
    !Array.isArray(value) &&
    Object.keys(value).length === 0
  );

const formatFieldName = (key) =>
  String(key)
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

const isUrl = (value) =>
  typeof value === 'string' &&
  /^https?:\/\/\S+$/i.test(value);

const formatMrp = (value) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `₹${value.toLocaleString('en-IN', {
      maximumFractionDigits: 2,
    })}`;
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();

    if (/^(₹|INR\b)/i.test(trimmed)) return trimmed;

    const numeric = Number(trimmed.replace(/,/g, ''));

    if (trimmed !== '' && Number.isFinite(numeric)) {
      return `₹${numeric.toLocaleString('en-IN', {
        maximumFractionDigits: 2,
      })}`;
    }

    return trimmed;
  }

  return String(value);
};

/*
 * IMPORTANT:
 * Render all values safely. Objects and arrays are converted into
 * readable JSX rather than being passed directly to React.
 */
function RenderValue({ value }) {
  if (isEmpty(value)) return <>—</>;

  if (typeof value === 'boolean') {
    return <>{value ? 'Yes' : 'No'}</>;
  }

  if (typeof value === 'number') {
    return <>{String(value)}</>;
  }

  if (typeof value === 'string') {
    if (isUrl(value)) {
      return (
        <a href={value} target="_blank" rel="noopener noreferrer">
          {value} ↗
        </a>
      );
    }

    return <>{value}</>;
  }

  if (Array.isArray(value)) {
    return (
      <div>
        {value.map((item, index) => (
          <div key={index} style={{ marginBottom: 7 }}>
            <RenderValue value={item} />
          </div>
        ))}
      </div>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value).filter(
      ([, nestedValue]) => !isEmpty(nestedValue)
    );

    if (entries.length === 0) return <>—</>;

    return (
      <div>
        {entries.map(([key, nestedValue]) => (
          <div
            key={key}
            style={{
              marginBottom: 8,
              overflowWrap: 'anywhere',
            }}
          >
            <strong style={{ color: '#a5b4fc' }}>
              {formatFieldName(key)}:
            </strong>{' '}
            <RenderValue value={nestedValue} />
          </div>
        ))}
      </div>
    );
  }

  return <>{String(value)}</>;
}

const FIELDS = [
  { key: 'description', label: 'Description', icon: '📝', fullWidth: true },
  { key: 'generic_name', label: 'Generic Name', icon: '🏷️' },
  { key: 'ingredients', label: 'Ingredients', icon: '🧪', fullWidth: true },
  { key: 'nutritional_info', label: 'Nutritional Information', icon: '📊', fullWidth: true },
  { key: 'best_before', label: 'Best Before / Expiry', icon: '📅' },
  { key: 'net_weight', label: 'Net Weight / Volume', icon: '⚖️' },
  { key: 'instructions', label: 'Usage Instructions', icon: '📋', fullWidth: true },
  { key: 'storage_instructions', label: 'Storage Instructions', icon: '🏠' },
  { key: 'allergens', label: 'Allergen Information', icon: '⚠️' },
  { key: 'manufacturer', label: 'Manufacturer', icon: '🏭' },
  { key: 'country_of_origin', label: 'Country of Origin', icon: '🌍' },
  { key: 'certifications', label: 'Certifications / Labels', icon: '✅' },
  { key: 'packaging', label: 'Packaging', icon: '📦' },
  { key: 'brand_owner', label: 'Brand Owner', icon: '🏢' },
  { key: 'additional_info', label: 'Additional Information', icon: 'ℹ️', fullWidth: true },
];

function ProductCard({ product, onReset, mrpLoading }) {
  if (!product || typeof product !== 'object') {
    return null;
  }

  const availableFields = FIELDS.filter(
    (field) => !isEmpty(product[field.key])
  );

  const hasMrp =
    product.mrp !== null &&
    product.mrp !== undefined &&
    product.mrp !== '';

  const rawResponse = product.raw_response;
  let parsedRawResponse = null;

  if (rawResponse && typeof rawResponse === 'string') {
    try {
      parsedRawResponse = JSON.parse(rawResponse);
    } catch {
      parsedRawResponse = null;
    }
  } else if (rawResponse && typeof rawResponse === 'object') {
    parsedRawResponse = rawResponse;
  }

  const sources = Array.isArray(product.sources)
    ? product.sources
    : [];

  const imageUrl =
    product.image_url ||
    product.image_front_url ||
    null;

  return (
    <Wrapper>
      {product.found === false && (
        <NotFoundBanner>
          ⚠️ The product could not be fully identified. Some details may
          come from supplementary research. Check the linked sources and
          package label before relying on them.
        </NotFoundBanner>
      )}

      <BarcodeDisplay>
        <div>
          <div
            style={{
              fontSize: '0.7rem',
              color: '#64748b',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              marginBottom: 4,
            }}
          >
            Barcode
          </div>
          <BarcodeText>║{product.barcode || '—'}║</BarcodeText>
        </div>

        {onReset && (
          <ResetButton type="button" onClick={onReset}>
            ↺ New Search
          </ResetButton>
        )}
      </BarcodeDisplay>

      <Header>
        <ProductMeta>
          {imageUrl && isUrl(imageUrl) ? (
            <img
              src={imageUrl}
              alt={product.product_name || 'Product'}
              style={{
                width: 90,
                height: 110,
                objectFit: 'contain',
                background: '#fff',
                borderRadius: 10,
                padding: 5,
              }}
              onError={(event) => {
                event.currentTarget.style.display = 'none';
              }}
            />
          ) : (
            <ProductEmoji>
              {getCategoryEmoji(product.category)}
            </ProductEmoji>
          )}

          <ProductInfo>
            <ProductName>
              {product.product_name || 'Unknown Product'}
            </ProductName>

            {product.brand && (
              <BrandBadge>🏷️ <RenderValue value={product.brand} /></BrandBadge>
            )}

            <TagRow>
              {!isEmpty(product.category) && (
                <Tag><RenderValue value={product.category} /></Tag>
              )}

              {!isEmpty(product.net_weight) && (
                <Tag><RenderValue value={product.net_weight} /></Tag>
              )}

              {!isEmpty(product.country_of_origin) && (
                <Tag>
                  🌍 <RenderValue value={product.country_of_origin} />
                </Tag>
              )}
            </TagRow>

            {product.verification_status && (
              <TagRow>
                <Tag>
                  Status: {formatFieldName(product.verification_status)}
                </Tag>
              </TagRow>
            )}
          </ProductInfo>

          {mrpLoading ? (
            <MrpLoadingBadge>
              <div className="label">MRP</div>
              <div className="price">fetching…</div>
            </MrpLoadingBadge>
          ) : hasMrp ? (
            <MrpBadge>
              <div className="label">MRP Candidate</div>
              <div className="price">{formatMrp(product.mrp)}</div>
            </MrpBadge>
          ) : null}
        </ProductMeta>
      </Header>

      {!hasMrp && !mrpLoading && product.found === false && (
        <Notice>
          💰 <strong>MRP not found.</strong> No MRP value was returned by
          the backend. Check the exact package or a reliable source.
        </Notice>
      )}

      {imageUrl && isUrl(imageUrl) && (
        <InfoCard style={{ marginBottom: 16 }}>
          <InfoCardLabel>Product Image</InfoCardLabel>
          <InfoCardValue>
            <a href={imageUrl} target="_blank" rel="noopener noreferrer">
              Open original product image ↗
            </a>
          </InfoCardValue>
        </InfoCard>
      )}

      <SectionTitle>📋 Product Details</SectionTitle>

      {availableFields.length > 0 ? (
        <Grid>
          {availableFields.map(({ key, label, icon, fullWidth }) => {
            const CardComponent = fullWidth ? FullWidthCard : InfoCard;

            return (
              <CardComponent key={key}>
                {icon && <InfoCardIcon>{icon}</InfoCardIcon>}
                <InfoCardLabel>{label}</InfoCardLabel>
                <InfoCardValue>
                  <RenderValue value={product[key]} />
                </InfoCardValue>
              </CardComponent>
            );
          })}
        </Grid>
      ) : (
        <Notice>
          No additional structured product details were returned by the API.
        </Notice>
      )}

      {sources.length > 0 && (
        <>
          <SectionTitle>🔗 Information Sources</SectionTitle>
          <InfoCard>
            {sources.map((source, index) => {
              const sourceText = String(source);

              return (
                <div key={`${sourceText}-${index}`} style={{ marginBottom: 10 }}>
                  {isUrl(sourceText) ? (
                    <a
                      href={sourceText}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#a5b4fc', overflowWrap: 'anywhere' }}
                    >
                      {sourceText} ↗
                    </a>
                  ) : (
                    <RenderValue value={sourceText} />
                  )}
                </div>
              );
            })}
          </InfoCard>
        </>
      )}

      {parsedRawResponse && (
        <>
          <SectionTitle>🔍 Full Database / Web Research</SectionTitle>
          <ExpandSection>
            <summary>Expand to inspect the complete raw lookup response</summary>
            <JsonBlock>
              {JSON.stringify(parsedRawResponse, null, 2)}
            </JsonBlock>
          </ExpandSection>
        </>
      )}

      {typeof rawResponse === 'string' && !parsedRawResponse && (
        <>
          <SectionTitle>🔍 Raw Lookup Response</SectionTitle>
          <ExpandSection>
            <summary>Expand raw response</summary>
            <JsonBlock>{rawResponse}</JsonBlock>
          </ExpandSection>
        </>
      )}

      {product.additional_info && (
        <Notice>
          <strong>Additional notes:</strong>{' '}
          <RenderValue value={product.additional_info} />
        </Notice>
      )}

      <Notice>
        A recognized barcode or online product record does not by itself
        establish authenticity. Treat an online MRP as a candidate until
        its source and exact pack size are checked.
      </Notice>
    </Wrapper>
  );
}

export default ProductCard;
