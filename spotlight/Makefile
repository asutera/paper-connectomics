spotlight.pdf: spotlight.tex beamerthemeRJH.sty
	pdflatex -shell-escape spotlight

all: spotlight.tex beamerthemeRJH.sty
	pdflatex -shell-escape spotlight && open spotlight.pdf


clean:
	rm -f *.log *.out *.aux *.bbl *.blg *.nav *.snm *.pyg *.toc *.pdf
