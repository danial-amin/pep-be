import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BarChart3,
  FileText,
  FolderOpen,
  MessageSquare,
  Play,
  Sparkles,
  Users,
} from 'lucide-react';

const PERSONA_BLUE = '#007aff';

function HighlightPersonaWords({ text }: { text: string }) {
  const parts = text.split(/(\bpersonas?\b)/gi);
  return (
    <>
      {parts.map((p, idx) => {
        const lower = p.toLowerCase();
        if (lower === 'persona' || lower === 'personas') {
          return (
            <span key={idx} style={{ color: PERSONA_BLUE, fontWeight: 700 }}>
              {p}
            </span>
          );
        }
        return <span key={idx}>{p}</span>;
      })}
    </>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs font-semibold text-stone-700">
      {children}
    </span>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="glass-card rounded-2xl p-6 hover:shadow-md transition-all duration-150">
      <div className="flex items-start gap-4">
        <div className="h-10 w-10 rounded-xl bg-stone-900 text-white flex items-center justify-center flex-shrink-0">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-stone-900">
            <HighlightPersonaWords text={title} />
          </h3>
          <p className="mt-1 text-sm leading-relaxed text-stone-600">
            <HighlightPersonaWords text={description} />
          </p>
        </div>
      </div>
    </div>
  );
}

function Step({
  n,
  icon: Icon,
  title,
  body,
}: {
  n: string;
  icon: React.ElementType;
  title: string;
  body: string;
}) {
  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <Badge>Step {n}</Badge>
        <Icon className="h-5 w-5 text-stone-400" />
      </div>
      <h4 className="text-lg font-semibold text-stone-900">
        <HighlightPersonaWords text={title} />
      </h4>
      <p className="mt-2 text-sm leading-relaxed text-stone-600">
        <HighlightPersonaWords text={body} />
      </p>
    </div>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="px-4 py-6 sm:px-0">
      {/* Hero */}
      <div className="glass-card rounded-3xl p-8 sm:p-10 overflow-hidden relative">
        {/* Soft animated background (subtle, chic) */}
        <div className="pointer-events-none absolute -top-28 -right-28 h-72 w-72 rounded-full bg-stone-900/5 blur-3xl pep-float-slower" />
        <div className="pointer-events-none absolute top-10 -left-20 h-56 w-56 rounded-full bg-stone-900/4 blur-3xl pep-float-slow" />
        <div className="pointer-events-none absolute -bottom-28 left-24 h-80 w-80 rounded-full bg-stone-900/5 blur-3xl pep-drift" />
        <div className="pointer-events-none absolute inset-0 opacity-[0.06]" style={{
          backgroundImage:
            'radial-gradient(closest-side at 12% 18%, rgba(0,0,0,0.08), transparent 60%), radial-gradient(closest-side at 88% 70%, rgba(0,0,0,0.06), transparent 58%)'
        }} />

        <div className="relative">
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <Badge><HighlightPersonaWords text="Persona  Engineering Platform" /></Badge>
            <Badge><HighlightPersonaWords text="RAG-grounded  personas" /></Badge>
            <Badge>Simulation playground</Badge>
          </div>

          <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-stone-900">
            <HighlightPersonaWords text="Turn messy research into personas you can actually use." />
          </h1>
          <p className="mt-4 text-stone-600 text-base sm:text-lg leading-relaxed max-w-3xl">
            <HighlightPersonaWords text="PEP helps you upload context + interview data, generate and refine persona sets, then run multi-persona simulations to pressure-test decisions. It’s built for clarity: clean profiles, fast workflows, and transcripts you can trust." />
          </p>

          <div className="mt-7 flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => navigate('/projects/new')}
              className="inline-flex items-center justify-center rounded-2xl bg-stone-900 px-6 py-3 text-white font-semibold hover:bg-stone-800 transition-all duration-200"
            >
              Create a project
              <ArrowRight className="ml-2 h-5 w-5" />
            </button>
            <button
              onClick={() => navigate('/projects')}
              className="inline-flex items-center justify-center rounded-2xl border border-stone-200 bg-white px-6 py-3 text-stone-900 font-semibold hover:bg-stone-50 transition-all duration-200"
            >
              Browse projects
              <FolderOpen className="ml-2 h-5 w-5 text-stone-700" />
            </button>
            <button
              onClick={() => navigate('/simulations')}
              className="inline-flex items-center justify-center rounded-2xl border border-stone-200 bg-white px-6 py-3 text-stone-900 font-semibold hover:bg-stone-50 transition-all duration-200"
            >
              Open simulation playground
              <Play className="ml-2 h-5 w-5 text-stone-700" />
            </button>
          </div>

          <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-stone-200 bg-white p-5">
              <div className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
                Input
              </div>
              <div className="mt-2 text-sm font-semibold text-stone-900">
                Context + Interviews
              </div>
              <div className="mt-1 text-sm text-stone-600">
                Upload research docs and transcripts.
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-white p-5">
              <div className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
                Output
              </div>
              <div className="mt-2 text-sm font-semibold text-stone-900">
                <HighlightPersonaWords text="Persona Sets" />
              </div>
              <div className="mt-1 text-sm text-stone-600">
                Profiles, images, diversity + validation.
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-white p-5">
              <div className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
                Stress test
              </div>
              <div className="mt-2 text-sm font-semibold text-stone-900">
                Simulations
              </div>
              <div className="mt-1 text-sm text-stone-600">
                <HighlightPersonaWords text="See how personas debate a goal." />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* What this is */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card rounded-3xl p-8">
          <h2 className="text-2xl font-bold text-stone-900">What PEP is</h2>
          <p className="mt-3 text-stone-600 leading-relaxed">
            <HighlightPersonaWords text="PEP is a workflow for generating personas from your project data, keeping them consistent, and using them in simulations to explore decisions. The goal is not “pretty personas” — it’s actionable stakeholder perspectives you can inspect, compare, and replay." />
          </p>

          <div className="mt-6 space-y-3">
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-stone-400 mt-0.5" />
              <p className="text-sm text-stone-700 leading-relaxed">
                <span className="font-semibold text-stone-900">Grounded generation:</span> persona
                responses are grounded in uploaded documents when relevant.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <Users className="h-5 w-5 text-stone-400 mt-0.5" />
              <p className="text-sm text-stone-700 leading-relaxed">
                <span className="font-semibold text-stone-900">Multi-persona simulations:</span> run
                conversations where each persona speaks in turns toward a shared goal.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <BarChart3 className="h-5 w-5 text-stone-400 mt-0.5" />
              <p className="text-sm text-stone-700 leading-relaxed">
                <span className="font-semibold text-stone-900">Evaluation & reporting:</span> measure
                diversity, validate against transcripts, and export outputs.
              </p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-3xl p-8">
          <h2 className="text-2xl font-bold text-stone-900">How it works</h2>
          <p className="mt-3 text-stone-600 leading-relaxed">
            <HighlightPersonaWords text="A simple loop: bring evidence in, generate personas, refine, and pressure-test with simulations." />
          </p>
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Step
              n="1"
              icon={FileText}
              title="Upload documents"
              body="Add context and interview transcripts. Processing runs in the background."
            />
            <Step
              n="2"
              icon={Sparkles}
              title="Generate personas"
              body="Create a set in JSON/profile/chat formats. Expand into richer profiles when ready."
            />
            <Step
              n="3"
              icon={Users}
              title="Review & optimize"
              body="Scan for coverage and gaps. Measure diversity and validate against your interviews."
            />
            <Step
              n="4"
              icon={Play}
              title="Run simulations"
              body="Select personas and a goal. Watch them discuss in rounds, with turn-by-turn transcripts."
            />
          </div>
        </div>
      </div>

      {/* Feature grid */}
      <div className="mt-8">
        <div className="flex items-end justify-between gap-4 mb-4">
          <div>
            <h2 className="text-2xl font-bold text-stone-900">Built for practical research teams</h2>
            <p className="mt-1 text-stone-600">
              Clear artifacts, consistent styling, and workflows that make sense.
            </p>
          </div>
          <button
            onClick={() => navigate('/personas')}
            className="hidden sm:inline-flex items-center rounded-xl bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-900 hover:bg-stone-100 transition-all"
          >
            Explore <span style={{ color: PERSONA_BLUE }}>personas</span> <ArrowRight className="ml-2 h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          <FeatureCard
            icon={FolderOpen}
            title="Projects as the organizing unit"
            description="Keep documents, persona sets, and outputs grouped so you can iterate without losing context."
          />
          <FeatureCard
            icon={FileText}
            title="Document processing + retrieval"
            description="Upload evidence once and let the system pull relevant chunks when personas respond."
          />
          <FeatureCard
            icon={Users}
            title="Persona sets you can inspect"
            description="From quick summaries to expanded full profiles, with images and downloadable JSON."
          />
          <FeatureCard
            icon={BarChart3}
            title="Diversity + validation signals"
            description="Measure set diversity and validate persona attributes against interview data where possible."
          />
          <FeatureCard
            icon={Play}
            title="Simulation playground"
            description="Run multi-persona discussions toward a goal; intervene as a facilitator; export transcripts."
          />
          <FeatureCard
            icon={MessageSquare}
            title="Readable transcripts"
            description="Turns are clearly marked and attributable, making it easy to quote, compare, and share."
          />
        </div>
      </div>

      {/* CTA footer */}
      <div className="mt-10 glass-card rounded-3xl p-8 sm:p-10">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="min-w-0">
            <h2 className="text-2xl font-bold text-stone-900">Start with a project</h2>
            <p className="mt-2 text-stone-600 leading-relaxed max-w-2xl">
              <HighlightPersonaWords text="If you already have context docs or interview transcripts, you can be generating personas in minutes. If you just want to explore, open the simulation playground and try a set." />
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
            <button
              onClick={() => navigate('/projects/new')}
              className="inline-flex items-center justify-center rounded-2xl bg-stone-900 px-6 py-3 text-white font-semibold hover:bg-stone-800 transition-all duration-200"
            >
              Create a project
              <ArrowRight className="ml-2 h-5 w-5" />
            </button>
            <button
              onClick={() => navigate('/projects')}
              className="inline-flex items-center justify-center rounded-2xl border border-stone-200 bg-white px-6 py-3 text-stone-900 font-semibold hover:bg-stone-50 transition-all duration-200"
            >
              View projects
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

