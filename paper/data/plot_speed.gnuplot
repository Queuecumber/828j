set terminal postscript enhanced color eps font "Helvetica, 30"
set size 1.2,1.2

set xlabel "Basis Size (bits)"
set ylabel  "Query Time (s)"

set logscale x 2

set xrange [16:4096]
set yrange [0:0.05]

set ytics 0,0.01,0.05
set xtics 16,4,4096

set xtics nomirror
set ytics nomirror

set grid ytics

set key tmargin horizontal

plot 'speed.csv' using 1:2 with linespoints title "LSH" linewidth 8 pointsize 5

of = "../images/hashing_time_results.eps"
set output of

l2(x) = 0.036580234
replot l2(x) title "l_2" linewidth 8
