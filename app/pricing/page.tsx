import { Header } from "@/components/landing/Header";
import { Pricing } from "@/components/landing/Pricing";
import { Footer } from "@/components/landing/Footer";
import { DemoModal } from "@/components/landing/DemoModal";

export const metadata = {
  title: "Tarifs — Songa",
  description: "Découvrez les offres Songa pour les clubs, académies et fédérations de basketball africaines.",
};

export default function PricingPage() {
  return (
    <main>
      <Header />
      <div className="pt-16">
        <Pricing />
      </div>
      <Footer />
      <DemoModal />
    </main>
  );
}
