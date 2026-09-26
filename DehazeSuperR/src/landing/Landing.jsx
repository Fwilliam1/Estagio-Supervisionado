import React, { useEffect } from 'react';
import './landing.css';

export default function Landing() {
  
  // Função de scroll para o topo adaptada para React
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Se você usava scripts externos (como bulma-carousel ou o slider), 
  // eles precisam ser inicializados aqui no useEffect.
  useEffect(() => {
    // Lógica para inicializar carrossel ou slider de imagens (se necessário)
    // Ex: bulmaCarousel.attach('#results-carousel', { ... });
  }, []);

  return (
    <>
      {/* Scroll to Top Button */}
      <button 
        className="scroll-to-top" 
        onClick={scrollToTop} 
        title="Scroll to top" 
        aria-label="Scroll to top"
        style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 99 }} // Adicionei um estilo básico para garantir que apareça
      >
        <i className="fas fa-chevron-up"></i>
      </button>

      <main id="main-content">
        <section className="hero">
          <div className="hero-body">
            <div className="container is-max-desktop">
              <div className="columns is-centered">
                <div className="column has-text-centered">
                  
                  <h1 className="title is-1 publication-title">Computational Vision Tasks for Image Reconstruction</h1>
                  
                  <div className="is-size-5 publication-authors">
                    <span className="author-block">Felipe William Freitas D'Avila, </span>
                    <span className="author-block">Emanuel de Souza Ramos</span>
                  </div>

                  <div className="is-size-5 publication-authors">
                    <span className="author-block">Universidade Federal do Acre - Ufac<br/>Laboratório de Pesquisa Aplicada em Visão e Inteligência Computacional</span>
                    <span className="eql-cntrb"><small><br/><sup>*</sup>PAVIC-Lab</small></span>
                  </div>

                  <div className="column has-text-centered">
                    <div className="publication-links">
                      <span className="link-block">
                        <a href="/" className="button is-normal is-rounded is-dark">
                          Acesso a aplicação
                        </a>
                      </span>
                                      
                      <span className="link-block">
                        <a href="https://github.com/YOUR_REPO_HERE" target="_blank" rel="noreferrer" className="external-link button is-normal is-rounded is-dark">
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
                    Essa aplicação é o produto final da disciplina de Estágio Supervisionado do 7º período do curso de bacharelado em Sistemas de Informação na Universidade Federal do Acre (Ufac) e desenvolvida para o PAVIC-Lab. O objetivo do projeto é desenvolver uma aplicação web que permita o processamento e generalização de imagens em três linhas de pesquisa desenvolvidas no PAVIC-Lab: Image Dehazing, Super-Resolução e HDR (High Dynamic Range).
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
              resolução a partir de uma imagem de baixa resolução. Seu objetivo é aumentar                                                                                                                                                                                                                                                                                                                                          
              a qualidade visual, recuperando detalhes e estruturas que foram perdidos                                                                                                                                                                                                                                                                                                                                              
              durante a aquisição ou redução da imagem.                                                                                                                                                                                                                                                                                                                                                                             
            </p>                                                                                                                                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                                                                                                                                                                                    
            <h3 className="title is-4">II – Image Dehazing</h3>                                                                                                                                                                                                                                                                                                                                                                         
            <p>                                                                                                                                                                                                                                                                                                                                                                                                                     
              Image Dehazing é a tarefa de remover os efeitos causados por neblina,                                                                                                                                                                                                                                                                                                                                                 
              fumaça ou outras partículas presentes na atmosfera, que reduzem a                                                                                                                                                                                                                                                                                                                                                     
              visibilidade e o contraste das imagens. O processo busca recuperar cores,                                                                                                                                                                                                                                                                                                                                             
              detalhes e informações visuais presentes na cena original.                                                                                                                                                                                                                                                                                                                                                            
            </p>                                                                                                                                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                                                                                                                                                                                    
            <h3 className="title is-4">III – HDR</h3>                                                                                                                                                                                                                                                                                                                                                        
            <p>                                                                                                                                                                                                                                                                                                                                                                                                                     
              A reconstrução de imagens em HDR (<em>High Dynamic Range</em>) consiste em                                                                                                                                                                                                                                                                                                                                            
              combinar informações de diferentes exposições para produzir uma imagem com                                                                                                                                                                                                                                                                                                                                            
              maior faixa dinâmica. Dessa forma, é possível representar simultaneamente                                                                                                                                                                                                                                                                                                                                             
              detalhes em regiões muito claras e muito escuras da cena.                                                                                                                                                                                                                                                                                                                                                             
            </p>                                                                                                                                                                                                                                                                                                                                                                                                                    
          </div>                                                                                                                                                                                                                                                                                                                                                                                                                    
        </section>

        {/* Image carousel */}
        <section className="hero is-small">
          <div className="hero-body">
            <div className="container">
              <h2 className="title is-3 has-text-centered">Diagramação das arquiteturas utilizadas</h2> 
              <div id="results-carousel" className="carousel results-carousel">
                <div className="item">
                  <img src="static/images/pipelineUDPNet.jpg" alt="First research result visualization" loading="lazy" />
                  <h2 className="subtitle has-text-centered">
                    UDPNet: Unleashing Depth-based Priors for Robust Image Dehazing.
                  </h2>
                </div>
                <div className="item">
                  <img src="static/images/convirpapelina.png" alt="Second research result visualization" loading="lazy" />
                  <h2 className="subtitle has-text-centered">
                    ConvIR: Revitalizing Convolutional Network for Image Restoration.
                  </h2>
                </div>
                <div className="item">
                  <img src="static/images/DMNet.png" alt="Third research result visualization" loading="lazy" />
                  <h2 className="subtitle has-text-centered">
                    DMNet: Dual-Domain Modulation Network.
                  </h2>
                </div>
                <div className="item">
                  <img src="static/images/ESC.jpg" alt="Fourth research result visualization" loading="lazy" />
                  <h2 className="subtitle has-text-centered">
                    ESC: Emulate Self-Attention with Convolution.
                  </h2>
                </div>
                <div className="item">
                  <img src="static/images/arquitetura_pshdr_2025_page-0001.jpg" alt="First research result visualization" loading="lazy" />
                  <h2 className="subtitle has-text-centered">
                    PSHDR: Pavic Single HDR.
                  </h2>
                </div>
                <div className="item">
                  <img src="static/images/arquitetura_safhdr_2026_page-0001.jpg" alt="First research result visualization" loading="lazy" />
                  <h2 className="subtitle has-text-centered">
                    SAFHDR: Single Attention Feature for HDR.
                  </h2>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Image Comparison */}
        <section className="hero is-small is-light">
          <div className="hero-body">
            <div className="container">
              <h2 className="title is-3 has-text-centered">Comparação Visual</h2>
            
              <div className="columns is-vcentered">
                {/* Menu Esquerdo (left-selector) */}
                <div className="column is-2">
                  <div className="method-selector left-selector">
                    <div className="field"><button className="button is-small is-success is-fullwidth" data-left="static/images/0009_0.8_0.16.jpg" data-right="static/images/0009_0.8_0.16_dehazed_UDPNet.png">UDPNet</button></div>
                    <div className="field"><button className="button is-small is-fullwidth" data-left="static/images/0001_0.8_0.2.jpg" data-right="static/images/0001_0.8_0.2_dehazed_ConvIR.png">ConvIR</button></div>
                    <div className="field"><button className="button is-small is-fullwidth" data-left="static/images/img_024.png" data-right="static/images/img_024_x4_DMNet.png">DMNet</button></div>
                    <div className="field"><button className="button is-small is-fullwidth" data-left="static/images/img_100.png" data-right="static/images/img_100_x4_ESC.png">ESC</button></div>
                    <div className="field"><button className="button is-small is-fullwidth" data-left="static/images/0212_medium.png" data-right="static/images/0212_medium_hdr_pshdr_reinhard.png">PSHDR</button></div>
                    <div className="field"><button className="button is-small is-fullwidth" data-left="static/images/0888_medium.png" data-right="static/images/0888_medium_hdr_safhdr_reinhard.png">SAFHDR</button></div>
                  </div>
                </div>

                {/* Container do Slider */}
                <div className="column is-8">
                  <div className="comparison-container" style={{ position: 'relative', width: '100%', boxShadow: '0 4px 10px rgba(0,0,0,0.2)', borderRadius: '4px', overflow: 'hidden', backgroundColor: '#000' }}>
                    
                    <div className="image-container">
                      <img src="static/images/0009_0.8_0.16_dehazed_UDPNet.png" alt="Ours Result" style={{ width: '100%', display: 'block', pointerEvents: 'none' }} />
                    </div>
                    
                    <div id="image2-container" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', clipPath: 'inset(0 50% 0 0)' }}>
                      <img src="static/images/0009_0.8_0.16.jpg" alt="Hazy Image" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', pointerEvents: 'none' }} />
                    </div>

                    <input type="range" min="0" max="100" defaultValue="50" id="comparison-slider" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', opacity: 0, cursor: 'ew-resize', zIndex: 30, margin: 0 }} />
                    
                    <div className="slider-line" id="slider-line" style={{ position: 'absolute', top: 0, bottom: 0, left: '50%', width: '4px', backgroundColor: 'white', transform: 'translateX(-50%)', pointerEvents: 'none', zIndex: 5 }}></div>
                    <div className="slider" id="slider-button" style={{ position: 'absolute', top: '50%', left: '50%', width: '30px', height: '30px', backgroundColor: 'white', borderRadius: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none', zIndex: 6 }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}