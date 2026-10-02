import { useState, useEffect } from 'react';
import './landing.css';

const COMPARISON_METHODS = [
  {
    id: 'UDPNet',
    name: 'UDPNet',
    left: '/static/images/0009_0.8_0.16.jpg',
    right: '/static/images/0009_0.8_0.16_dehazed_UDPNet.png',
    leftLabel: 'Imagem com Neblina (Input)',
    rightLabel: 'Dehazing (UDPNet)',
  },
  {
    id: 'ConvIR',
    name: 'ConvIR',
    left: '/static/images/0001_0.8_0.2.jpg',
    right: '/static/images/0001_0.8_0.2_dehazed_ConvIR.png',
    leftLabel: 'Imagem com Neblina (Input)',
    rightLabel: 'Dehazing (ConvIR)',
  },
  {
    id: 'DMNet',
    name: 'DMNet',
    left: '/static/images/img_024.png',
    right: '/static/images/img_024_x4_DMNet.png',
    leftLabel: 'Baixa Resolução (Input)',
    rightLabel: 'Super-Resolução X4 (DMNet)',
  },
  {
    id: 'ESC',
    name: 'ESC',
    left: '/static/images/img_100.png',
    right: '/static/images/img_100_x4_ESC.png',
    leftLabel: 'Baixa Resolução (Input)',
    rightLabel: 'Super-Resolução X4 (ESC)',
  },
  {
    id: 'PSHDR',
    name: 'PSHDR',
    left: '/static/images/0212_medium.png',
    right: '/static/images/0212_medium_hdr_pshdr_reinhard.png',
    leftLabel: 'Baixa Faixa Dinâmica (LDR)',
    rightLabel: 'Reconstrução HDR (PSHDR + Reinhard)',
  },
  {
    id: 'SAFHDR',
    name: 'SAFHDR',
    left: '/static/images/0888_medium.png',
    right: '/static/images/0888_medium_hdr_safhdr_reinhard.png',
    leftLabel: 'Baixa Faixa Dinâmica (LDR)',
    rightLabel: 'Reconstrução HDR (SAFHDR + Reinhard)',
  },
];

const ARCHITECTURE_SLIDES = [
  {
    img: '/static/images/pipelineUDPNet.jpg',
    title: 'Dehazing - UDPNet: Unleashing Depth-based Priors for Robust Image Dehazing.',
  },
  {
    img: '/static/images/convirpapelina.png',
    title: 'Dehazing - ConvIR: Revitalizing Convolutional Network for Image Restoration.',
  },
  {
    img: '/static/images/DMNet.png',
    title: 'Super-Resolução - DMNet: Dual-Domain Modulation Network.',
  },
  {
    img: '/static/images/ESC.jpg',
    title: 'Super-Resolução - ESC: Emulate Self-Attention with Convolution.',
  },
  {
    img: '/static/images/arquitetura_pshdr_2025_page-0001.jpg',
    title: 'Recosntrução HDR - PSHDR: Pavic Single HDR.',
  },
  {
    img: '/static/images/arquitetura_safhdr_2026_page-0001.jpg',
    title: 'Recosntrução HDR - SAFHDR: Single Attention Feature for HDR.',
  },
];

export default function Landing({ onNavigateToApp, onNavigateToLogin }) {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [selectedMethodId, setSelectedMethodId] = useState('UDPNet');
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);

  const activeMethod =
    COMPARISON_METHODS.find((m) => m.id === selectedMethodId) ||
    COMPARISON_METHODS[0];

  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 300);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateApp = (e) => {
    if (e) e.preventDefault();
    if (onNavigateToLogin) {
      onNavigateToLogin();
    } else if (onNavigateToApp) {
      onNavigateToApp();
    } else {
      window.location.hash = '#login';
    }
  };

  return (
    <div className="landing-page-root">
      {/* Scroll to Top Button */}
      <button
        type="button"
        className={`scroll-to-top ${showScrollTop ? 'visible' : ''}`}
        onClick={scrollToTop}
        title="Scroll to top"
        aria-label="Scroll to top"
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 99,
          display: showScrollTop ? 'flex' : 'none',
        }}
      >
        <i className="fas fa-chevron-up"></i>
      </button>

      <main id="main-content">
        <section className="hero">
          <div className="hero-body">
            <div className="container is-max-desktop">
              <div className="columns is-centered">
                <div className="column has-text-centered">
                  <h1 className="title is-1 publication-title">
                    Computational Vision Tasks for Image Reconstruction (CVT-IR)
                  </h1>

                  <div className="is-size-5 publication-authors">
                    <span className="author-block">
                      Felipe William Freitas D'Avila,{' '}
                    </span>
                    <span className="author-block">
                      Emanuel de Souza Ramos
                    </span>
                  </div>

                  <div className="is-size-5 publication-authors">
                    <span className="author-block">
                      Universidade Federal do Acre - Ufac
                      <br />
                      Laboratório de Pesquisa Aplicada em Visão e Inteligência
                      Computacional
                    </span>
                    <span className="eql-cntrb">
                      <small>
                        <br />
                        <sup>*</sup>PAVIC-Lab
                      </small>
                    </span>
                  </div>

                  <div className="publication-links">
                    <span className="link-block">
                      <a
                        href="#app"
                        role="button"
                        onClick={handleNavigateApp}
                        className="external-link button is-normal is-rounded is-dark"
                      >
                        <span>Acesso à Aplicação</span>
                      </a>
                    </span>

                    <span className="link-block">
                      <a
                        href="https://github.com/Fwilliam1/Estagio-Supervisionado"
                        target="_blank"
                        rel="noreferrer"
                        className="external-link button is-normal is-rounded is-dark"
                      >
                        <span className="icon">
                          <i className="fab fa-github"></i>
                        </span>
                        <span>Code</span>
                      </a>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Paper abstract */}
        <section className="section hero is-light">
          <div className="container is-max-desktop">
            <div className="columns is-centered has-text-centered">
              <div className="column is-four-fifths">
                <h2 className="title is-3">Apresentação</h2>
                <div className="content has-text-justified">
                  <p>
                    Essa aplicação é o produto final da disciplina de Estágio
                    Supervisionado do 7º período do curso de bacharelado em
                    Sistemas de Informação na Universidade Federal do Acre
                    (Ufac) e desenvolvida para o PAVIC-Lab. O objetivo do
                    projeto é desenvolver uma aplicação web que permita o
                    processamento e generalização de imagens em três linhas de
                    pesquisa desenvolvidas no PAVIC-Lab: Image Dehazing,
                    Super-Resolução e HDR (High Dynamic Range).
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Texto explicativo das áreas de pesquisa */}
        <section className="section">
          <div className="container content">
            <h3 className="title is-4">I – Super-Resolução</h3>
            <p>
              A Super-Resolução é o processo de reconstruir uma imagem de alta
              resolução a partir de uma imagem de baixa resolução. Seu objetivo
              é aumentar a qualidade visual, recuperando detalhes e estruturas
              que foram perdidos durante a aquisição ou redução da imagem.
            </p>

            <h3 className="title is-4">II – Image Dehazing</h3>
            <p>
              Image Dehazing é a tarefa de remover os efeitos causados por
              neblina, fumaça ou outras partículas presentes na atmosfera, que
              reduzem a visibilidade e o contraste das imagens. O processo busca
              recuperar cores, detalhes e informações visuais presentes na cena
              original.
            </p>

            <h3 className="title is-4">III – HDR</h3>
            <p>
              A reconstrução de imagens em HDR (<em>High Dynamic Range</em>)
              consiste em combinar informações de diferentes exposições para
              produzir uma imagem com maior faixa dinâmica. Dessa forma, é
              possível representar simultaneamente detalhes em regiões muito
              claras e muito escuras da cena.
            </p>
          </div>
        </section>

        {/* Image carousel */}
        <section className="hero is-small">
          <div className="hero-body">
            <div className="container">
              <h2 className="title is-3 has-text-centered">
                Diagramação das arquiteturas utilizadas
              </h2>
              <div
                style={{
                  position: 'relative',
                  maxWidth: '850px',
                  margin: '0 auto',
                }}
              >
                <div
                  style={{
                    textAlign: 'center',
                    backgroundColor: '#fff',
                    padding: '1.25rem',
                    borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
                  }}
                >
                  <img
                    src={ARCHITECTURE_SLIDES[currentSlide].img}
                    alt={ARCHITECTURE_SLIDES[currentSlide].title}
                    style={{
                      maxHeight: '440px',
                      maxWidth: '100%',
                      objectFit: 'contain',
                      margin: '0 auto',
                      display: 'block',
                    }}
                  />
                  <h3
                    className="subtitle is-5 has-text-centered"
                    style={{ marginTop: '1rem', fontWeight: 600 }}
                  >
                    {ARCHITECTURE_SLIDES[currentSlide].title}
                  </h3>
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    gap: '1rem',
                    marginTop: '1rem',
                  }}
                >
                  <button
                    type="button"
                    className="button is-small is-rounded is-dark"
                    onClick={() =>
                      setCurrentSlide((prev) =>
                        prev > 0 ? prev - 1 : ARCHITECTURE_SLIDES.length - 1
                      )
                    }
                    title="Slide anterior"
                  >
                    Anterior
                  </button>
                  <span style={{ fontSize: '0.9rem', color: '#666' }}>
                    {currentSlide + 1} / {ARCHITECTURE_SLIDES.length}
                  </span>
                  <button
                    type="button"
                    className="button is-small is-rounded is-dark"
                    onClick={() =>
                      setCurrentSlide((prev) =>
                        prev < ARCHITECTURE_SLIDES.length - 1 ? prev + 1 : 0
                      )
                    }
                    title="Próximo slide"
                  >
                    Próximo
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Image Comparison */}
        <section className="hero is-small is-light">
          <div className="hero-body">
            <div className="container">
              <h2 className="title is-3 has-text-centered">
                Comparação Visual
              </h2>

              {/* Seletor de Métodos Centralizado */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '10px',
                  margin: '1.5rem auto',
                  maxWidth: '850px',
                }}
              >
                {COMPARISON_METHODS.map((method) => (
                  <button
                    type="button"
                    key={method.id}
                    className={`button is-normal is-rounded ${
                      selectedMethodId === method.id
                        ? 'is-success'
                        : 'is-white'
                    }`}
                    onClick={() => setSelectedMethodId(method.id)}
                    style={{
                      fontWeight: selectedMethodId === method.id ? 700 : 500,
                      padding: '0 1.25rem',
                      boxShadow: '0 2px 6px rgba(0,0,0,0.08)',
                    }}
                  >
                    {method.name}
                  </button>
                ))}
              </div>

              {/* Container da Imagem com Slider Centralizada */}
              <div
                style={{
                  maxWidth: '850px',
                  margin: '0 auto',
                }}
              >
                <div
                  className="comparison-container"
                  style={{
                    position: 'relative',
                    width: '100%',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    backgroundColor: '#000',
                    userSelect: 'none',
                  }}
                >
                  {/* Imagem Base (Resultado do Modelo / Direita) */}
                  <div className="image-container">
                    <img
                      src={activeMethod.right}
                      alt={activeMethod.rightLabel}
                      style={{
                        width: '100%',
                        display: 'block',
                        pointerEvents: 'none',
                      }}
                    />
                  </div>

                  {/* Imagem Sobreposta (Entrada / Esquerda) */}
                  <div
                    id="image2-container"
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      clipPath: `inset(0 ${100 - sliderPosition}% 0 0)`,
                    }}
                  >
                    <img
                      src={activeMethod.left}
                      alt={activeMethod.leftLabel}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        display: 'block',
                        pointerEvents: 'none',
                      }}
                    />
                  </div>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={sliderPosition}
                    onChange={(e) =>
                      setSliderPosition(Number(e.target.value))
                    }
                    id="comparison-slider"
                    aria-label="Deslize para comparar a imagem original com o resultado"
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      opacity: 0,
                      cursor: 'ew-resize',
                      zIndex: 30,
                      margin: 0,
                    }}
                  />

                  <div
                    className="slider-line"
                    id="slider-line"
                    style={{
                      position: 'absolute',
                      top: 0,
                      bottom: 0,
                      left: `${sliderPosition}%`,
                      width: '4px',
                      backgroundColor: 'white',
                      transform: 'translateX(-50%)',
                      pointerEvents: 'none',
                      zIndex: 5,
                    }}
                  ></div>
                  <div
                    className="slider"
                    id="slider-button"
                    style={{
                      position: 'absolute',
                      top: '50%',
                      left: `${sliderPosition}%`,
                      width: '30px',
                      height: '30px',
                      backgroundColor: 'white',
                      borderRadius: '50%',
                      transform: 'translate(-50%, -50%)',
                      pointerEvents: 'none',
                      zIndex: 6,
                      boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
                    }}
                  ></div>
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginTop: '10px',
                    fontSize: '13px',
                    color: '#555',
                    fontWeight: 600,
                  }}
                >
                  <span>← {activeMethod.leftLabel}</span>
                  <span>{activeMethod.rightLabel} →</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}