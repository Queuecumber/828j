set terminal postscript enhanced color eps font "Helvetica, 30"
set size 1.2,1.2

set xlabel "Basis Size (bits)"
set ylabel  "Database Size (kB)"

set logscale x 2

set xrange [16:4096]
set yrange [0:5000]

set xtics 16,4,4096
set ytics 0,1000,5000

set xtics nomirror
set ytics nomirror

set grid ytics

set key tmargin horizontal

plot 'space.csv' using 1:2 with linespoints title "LSH" linewidth 8 pointsize 5

of = "../images/hashing_memory_results.eps"
set output of

emb(x) = 4096
replot emb(x) title "Embedding" linewidth 8
