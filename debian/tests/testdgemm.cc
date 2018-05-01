#include <iostream>
#include <cstdlib>
#include <cassert>

//#include <cblas.h>
//#include <mkl.h>
#include <mkl_cblas.h>  /* MKL - CBLAS Part */

#include <sys/time.h>

// This file is used to test correctness of cblas header / library packaging.
// Although can be used as a very rough benchmarker.
// g++ testdgemm.cc $(pkg-config --libs --cflags mkl-rt)

const int iteration = 5; // how many iterations would you like to run
const int repeat = 100; // repeat several times in each iteration
const int M = 512; // matrix size (M * M) used for testing
const bool debug = false; // dump the matrices?

void
ddump2(const size_t m, const size_t n, double* x, const size_t incx)
// dump a M by N matrix.
{
	for (size_t i = 0; i < m; i++) {
		for (size_t j = 0; j < n; j++) {
			printf(" %lf", x[i*m + j]);
		}
		printf("\n");
	}
	return;
}

int
main(void)
{
	struct timeval tv_start, tv_end;

	double* x = (double*)malloc(sizeof(double) * M * M);
	double* y = (double*)malloc(sizeof(double) * M * M);
	double* z = (double*)malloc(sizeof(double) * M * M);

	// check sanity first. Doing things fast but wrong is in vain.
	for (int i = 0; i < M*M; i++) {
		x[i] = drand48();
	}
	for (int i = 0; i < M; i++) {
		y[i*M + i] = 1.;
	}
	if (debug) ddump2(M, M, x, 1);
	if (debug) ddump2(M, M, y, 1);
	cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
			M, M, M, 1., x, M, y, M, 0., z, M);  // z <- x * I
	if (debug) ddump2(M, M, z, 1);
	cblas_daxpy(M*M, -1., x, 1, z, 1); // z <- -x + z
	if (debug) ddump2(M, M, z, 1);
	double error = cblas_dasum(M*M, z, 1);
	fprintf(stdout, "Sanity Test Error: %lf\n", error);
	assert(error < 1e-9);

	// start iterations
	for (int t = 0; t < iteration; t++) {

		// fill the matrices and run dgemm for several times
		for (int i = 0; i < M*M; i++) {
			x[i] = drand48(); 
			y[i] = drand48();
		}

		// run dgemm
		gettimeofday(&tv_start, nullptr);
		for (int i = 0; i < repeat; i++) {
			cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
				M, M, M, 1., x, M, y, M, 0., z, M);
			cblas_dgemm(CblasRowMajor, CblasTrans, CblasNoTrans,
				M, M, M, 1., x, M, y, M, 0., z, M);
			cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasTrans,
				M, M, M, 1., x, M, y, M, 0., z, M);
			cblas_dgemm(CblasRowMajor, CblasTrans, CblasTrans,
				M, M, M, 1., x, M, y, M, 0., z, M);
		}
		gettimeofday(&tv_end, nullptr);
		fprintf(stdout, "(%d/%d) Elapsed %.3lf ms\n", t+1, repeat,
				(tv_end.tv_sec*1e6 + tv_end.tv_usec
				 - tv_start.tv_sec*1e6  - tv_start.tv_usec)/1e3);
	}

	return 0;
}
