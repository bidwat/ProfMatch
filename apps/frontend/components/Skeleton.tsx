export function SkeletonLine({ width = '100%', height = 12 }: { width?: string; height?: number }) {
  return <span className="skeleton-line" style={{ width, height }} aria-hidden="true" />;
}

export function ProfessorCardSkeleton() {
  return (
    <div className="card skeleton-card" aria-hidden="true">
      <div className="card-top">
        <div className="identity">
          <span className="skeleton-avatar" />
          <div style={{ display: 'grid', gap: 8, minWidth: 220 }}>
            <SkeletonLine width="160px" height={16} />
            <SkeletonLine width="260px" height={11} />
          </div>
        </div>
        <div style={{ display: 'grid', justifyItems: 'end', gap: 6 }}>
          <SkeletonLine width="38px" height={22} />
          <SkeletonLine width="52px" height={10} />
        </div>
      </div>
      <div className="tags"><SkeletonLine width="92px" height={22} /><SkeletonLine width="132px" height={22} /><SkeletonLine width="108px" height={22} /></div>
      <SkeletonLine width="100%" height={13} />
      <SkeletonLine width="94%" height={13} />
      <SkeletonLine width="72%" height={13} />
      <div className="actions"><SkeletonLine width="82px" height={32} /><SkeletonLine width="72px" height={32} /></div>
    </div>
  );
}

export function ProfessorListSkeleton({ count = 4 }: { count?: number }) {
  return <>{Array.from({ length: count }, (_, index) => <ProfessorCardSkeleton key={index} />)}</>;
}

export function PageSkeleton() {
  return (
    <div className="page">
      <div className="skeleton-page-heading">
        <SkeletonLine width="220px" height={28} />
        <SkeletonLine width="420px" height={14} />
      </div>
      <div className="grid" style={{ marginBottom: 20 }}>
        <div className="card"><SkeletonLine width="70px" height={28} /><SkeletonLine width="120px" height={12} /></div>
        <div className="card"><SkeletonLine width="70px" height={28} /><SkeletonLine width="120px" height={12} /></div>
        <div className="card"><SkeletonLine width="70px" height={28} /><SkeletonLine width="120px" height={12} /></div>
      </div>
      <ProfessorListSkeleton count={3} />
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="page narrow">
      <div className="card skeleton-card">
        <div className="row between" style={{ marginBottom: 18 }}><SkeletonLine width="80px" height={14} /><SkeletonLine width="76px" height={32} /></div>
        <div className="professor-sticky-main">
          <span className="skeleton-avatar large" />
          <div style={{ display: 'grid', gap: 10, flex: 1 }}>
            <SkeletonLine width="240px" height={30} />
            <SkeletonLine width="320px" height={14} />
            <SkeletonLine width="220px" height={14} />
          </div>
          <div><SkeletonLine width="42px" height={30} /><SkeletonLine width="48px" height={10} /></div>
        </div>
        <div className="tags"><SkeletonLine width="120px" height={22} /><SkeletonLine width="96px" height={22} /><SkeletonLine width="150px" height={22} /></div>
      </div>
      <div className="card" style={{ marginTop: 16 }}><SkeletonLine width="180px" height={18} /><SkeletonLine width="100%" height={13} /><SkeletonLine width="92%" height={13} /><SkeletonLine width="80%" height={13} /></div>
    </div>
  );
}
