#include <iostream>
#include <cstdlib>

//#include <cblas.h>
//#include <mkl.h>
#include <mkl_cblas.h>  /* MKL - CBLAS Part */

#include <sys/time.h>

// This file is used to test correctness of cblas header / library packaging.
// Although can be used as a very rough benchmarker.
// g++ testdgemm.cc $(pkg-config --libs --cflags mkl-rt)

const int repeat = 100;
const int M = 512;

int
main(void)
{
	struct timeval tv_start, tv_end;

	double* x = (double*)malloc(sizeof(double) * M * M);
	double* y = (double*)malloc(sizeof(double) * M * M);
	double* z = (double*)malloc(sizeof(double) * M * M);
	for (int i = 0; i < M*M; i++) {
		x[i] = drand48(); 
		y[i] = drand48();
	}

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
    fprintf(stdout, "Elapsed %.3lf ms\n",
			(tv_end.tv_sec*1e6 + tv_end.tv_usec
			 - tv_start.tv_sec*1e6  - tv_start.tv_usec)/1e3);
	return 0;
}
