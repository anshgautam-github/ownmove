import React from 'react';
import DecisionCard from './DecisionCard';
import ProblemSolvingCard from './ProblemSolvingCard';
import EvaluationCard from './EvaluationCard';
import RoutingCTA from './RoutingCTA';

/**
 * Renders one assistant turn. Deliberately NOT the same visual template
 * every time — which card (if any) renders depends entirely on which
 * field of `structured_content` is populated, so a short general answer
 * stays short and a decision/evaluation/problem-solving answer gets its
 * own structured layout. Never shown as 8 identical cards.
 */
export default function AssistantMessage({ message, onNavigateTab }) {
  const structured = message.structured_content;

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#161616] text-[11px] font-black text-white">
          AI
        </span>
        <div className="min-w-0 flex-1 rounded-[16px] rounded-tl-[4px] border border-white/70 bg-white/70 p-3.5">
          <p className="text-[14px] font-semibold leading-relaxed text-[#1a1a1a]">{message.content}</p>
          {structured?.clarifying_question && (
            <p className="mt-2 text-[13px] font-bold italic text-[#5c46c9]">{structured.clarifying_question}</p>
          )}
        </div>
      </div>

      {structured?.routing && (
        <div className="ml-9">
          <RoutingCTA routing={structured.routing} onNavigateTab={onNavigateTab} />
        </div>
      )}

      {structured?.decision && (
        <div className="ml-9">
          <DecisionCard decision={structured.decision} />
        </div>
      )}
      {structured?.problem_solving && (
        <div className="ml-9">
          <ProblemSolvingCard problemSolving={structured.problem_solving} />
        </div>
      )}
      {structured?.evaluation && (
        <div className="ml-9">
          <EvaluationCard evaluation={structured.evaluation} />
        </div>
      )}
    </div>
  );
}
