#!/usr/bin/julia-0.6.2
# Compare performance among different BLAS implementations
# Reference: Julia/stdlib/LinearAlgebra/src/blas.jl

const N1 = 65536  # N for level1 calls
const N3 = 4096   # N for level3 calls
const netlibblas = "/usr/lib/x86_64-linux-gnu/blas/libblas.so.3.8.0"
const atlas      = "/usr/lib/x86_64-linux-gnu/atlas/libblas.so.3.10.3"
const openblas   = "/usr/lib/x86_64-linux-gnu/libopenblasp-r0.2.20.so"
const mkl        = "/usr/lib/x86_64-linux-gnu/libmkl_rt.so"


julia_nrm2 = false
for libblas in (netlibblas, atlas, openblas, mkl)
	@eval begin
		function ffi_nrm2(n::Integer, X::Union{Ptr{Float64}, AbstractArray{Float64}}, incx::Integer)
			ccall((:dnrm2_, $libblas), Float64, (Ref{Int64}, Ptr{Float64}, Ref{Int64}), n, X, incx)
		end
	end
	x = rand(N1)
	if !julia_nrm2
		println("\x1b[1;31mdnrm2 Julia\x1b[m")
		norm(x)  # JIT
		@time norm(x)
		julia_nrm2 = true
	end
	println("\x1b[1;31mdnrm2 ", libblas, "\x1b[m")
	ffi_nrm2(N1, x, 1)  # JIT
	@time ffi_nrm2(N1, x, 1)

	println("  dnrm2 Error :", abs(norm(x) - ffi_nrm2(N1, x, 1)))  # correctness
end

julia_dgemm = false
for libblas in (netlibblas, atlas, openblas, mkl)
	@eval begin
		function ffi_gemm!(transA::Char, transB::Char,
						   alpha::Float64, A::AbstractVecOrMat{Float64},
						   B::AbstractVecOrMat{Float64}, beta::Float64,
						   C::AbstractVecOrMat{Float64})
			m = size(A, transA == 'N' ? 1 : 2)
            ka = size(A, transA == 'N' ? 2 : 1)
            kb = size(B, transB == 'N' ? 1 : 2)
            n = size(B, transB == 'N' ? 2 : 1) 
            ccall((:dgemm_, $libblas), Void,
                (Ref{UInt8}, Ref{UInt8}, Ref{Int64}, Ref{Int64},
                 Ref{Int64}, Ref{Float64}, Ptr{Float64}, Ref{Int64},
                 Ptr{Float64}, Ref{Int64}, Ref{Float64}, Ptr{Float64},
                 Ref{Int64}),
                 transA, transB, m, n,
                 ka, alpha, A, max(1,stride(A,2)),
                 B, max(1,stride(B,2)), beta, C,
                 max(1,stride(C,2)))
		end
	end
	x, y, z = rand(N3, N3), rand(N3, N3), zeros(N3, N3)
	if !julia_dgemm
		println("\x1b[1;31mdgemm Julia\x1b[m")
		Base.BLAS.gemm('N', 'N', x, y)  # JIT
		@time Base.BLAS.gemm('N', 'N', x, y)
		julia_dgemm = true
	end
	println("\x1b[1;31mdgemm ", libblas, "\x1b[m")
	ffi_gemm!('N', 'N', 1., x, y, 0., z)  # JIT
	@time ffi_gemm!('N', 'N', 1., x, y, 0., z)

	z2 = Base.BLAS.gemm('N', 'N', x, y)
	ffi_gemm!('N', 'N', 1., x, y, 0., z)
	println("  dgemm Error :", norm(z2 - z))  # correctness
end
