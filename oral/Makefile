slides.pdf: slides.tex beamerthemeRJH.sty
	pdflatex -shell-escape slides

all: slides.tex beamerthemeRJH.sty
	pdflatex -shell-escape slides && open slides.pdf


clean:
	rm -f *.log *.out *.aux *.bbl *.blg *.nav *.snm *.pyg *.toc *.pdf
