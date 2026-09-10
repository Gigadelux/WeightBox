"use client";
import { Unavailable } from "@/components/states";
export default function ErrorPage({ reset }) {
  return (
    <main
      id="main"
      className="page-shell max-w-378 my-0 mx-auto pt-10.5 px-12 pb-16.25 max-[1190px]:px-7.5 max-[850px]:pt-7.5 max-[850px]:px-6 max-[850px]:pb-11.25 max-[620px]:pt-7 max-[620px]:px-4.5 max-[620px]:pb-8.75"
    >
      <Unavailable
        onRetry={reset}
        title="We couldn’t open the workbench."
        detail="Something interrupted this request. Try loading the page again."
      />
    </main>
  );
}
