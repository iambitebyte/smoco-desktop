import SEO from '../components/SEO'
import Hero from '../components/home/Hero'
import ProblemSolution from '../components/home/ProblemSolution'
import Features from '../components/home/Features'
import UseCases from '../components/home/UseCases'
import QuickStart from '../components/home/QuickStart'
import Gallery from '../components/home/Gallery'
import DownloadCTA from '../components/home/DownloadCTA'
import RoadmapSection from '../components/home/RoadmapSection'

export default function Home() {
  return (
    <>
      <SEO titleKey="seo.home.title" descriptionKey="seo.home.description" />
      <Hero />
      <ProblemSolution />
      <Features />
      <UseCases />
      <QuickStart />
      <Gallery />
      <DownloadCTA />
      <RoadmapSection />
    </>
  )
}
