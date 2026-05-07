import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { StatsBar } from "@/components/landing/StatsBar";
import { ProductShowcase } from "@/components/landing/ProductShowcase";
import { Features } from "@/components/landing/Features";
import { SocialProof } from "@/components/landing/SocialProof";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Pricing } from "@/components/landing/Pricing";
import { Audience } from "@/components/landing/Audience";
import { Footer } from "@/components/landing/Footer";
import { DemoModal } from "@/components/landing/DemoModal";

export default function Page() {
  return (
    <main>
      <Header />
      <Hero />
      <StatsBar />
      <ProductShowcase />
      <Features />
      <SocialProof />
      <HowItWorks />
      <Pricing />
      <Audience />
      <Footer />
      <DemoModal />
    </main>
  );
}
