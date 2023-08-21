/**********************************************************************/
/* (C) Crown copyright Met Office. All rights reserved.               */
/* For further details please refer to the file LICENCE.txt           */
/* which you should have received as part of this distribution.       */
/* *****************************COPYRIGHT******************************/
/*                                                                    */
/* This file is part of the UM SSTPert library extension module       */
/* for use with Mule.                                                 */
/*                                                                    */
/* Mule is free software: you can redistribute it and/or modify it    */
/* under the terms of the Modified BSD License, as published by the   */
/* Open Source Initiative.                                            */
/*                                                                    */
/* Mule is distributed in the hope that it will be useful,            */
/* but WITHOUT ANY WARRANTY; without even the implied warranty of     */
/* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      */
/* Modified BSD License for more details.                             */
/*                                                                    */
/* You should have received a copy of the Modified BSD License        */
/* along with Mule.                                                   */
/* If not, see <http://opensource.org/licenses/BSD-3-Clause>.         */
/* ********************************************************************/

#ifndef NPY_1_7_API_VERSION
#define NPY_1_7_API_VERSION 0x00000007
#endif

#ifndef NPY_NO_DEPRECATED_API
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#endif

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <numpy/arrayobject.h>

#include "sstpert.h"

#if PY_MAJOR_VERSION >= 3
#define PyInt_FromLong PyLong_FromLong
#define MOD_ERROR_VAL NULL
#define MOD_SUCCESS_VAL(val) val
#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  static struct PyModuleDef moduledef = {             \
    PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
  ob = PyModule_Create(&moduledef);
#else
#define MOD_ERROR_VAL
#define MOD_SUCCESS_VAL(val)
#define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  ob = Py_InitModule3(name, methods, doc);
#endif

MOD_INIT(um_sstpert);

static PyObject *sstpert_py(PyObject *self, PyObject *args);
static PyObject *sstpertseed_py(PyObject *self, PyObject *args);

MOD_INIT(um_sstpert)
{
  PyDoc_STRVAR(um_sstpert__doc__,
  "This extension module provides access to the UM SST perturbation library.\n"
  );

  PyDoc_STRVAR(sstpert__doc__,
  "Generate a SST perturbation field from a climatology and target date.\n\n"
  "Usage:\n"
  "  um_sstpert.sstpert(factor, dt, climatology)\n\n"
  "Args:\n"
  "* factor      - alpha factor for perturbation generation.\n"
  "* dt          - 8 element array giving year, month, day, hour, offset,\n"
  "                minutes, ensemble member number and ensemble member + 100.\n"
  "* climatology - 3 Dimensional numpy.ndarray giving climatologies; the \n"
  "                dimensions are rows, columns, and 12 (months).\n\n"
  "Returns:\n"
  "  2 Dimensional numpy.ndarray containing SST pert field data.\n"
  );

  PyDoc_STRVAR(sstpertseed__doc__,
  "Generate a random seed from a target date.\n\n"
  "Usage:\n"
  "  um_sstpert.sstpertseed(dt)\n\n"
  "Args:\n"
  "* dt          - 8 element array giving year, month, day, hour, offset,\n"
  "                minutes, ensemble member number and ensemble member + 100.\n"
  "Returns:\n"
  "  Random seed value\n"
  );


  static PyMethodDef um_sstpertMethods[] = {
    {"sstpert", sstpert_py, METH_VARARGS, sstpert__doc__},
    {"sstpertseed", sstpertseed_py, METH_VARARGS, sstpertseed__doc__},
    {NULL, NULL, 0, NULL}
  };

  PyObject *mod;
  MOD_DEF(mod, "um_sstpert", um_sstpert__doc__, um_sstpertMethods);
  if (mod == NULL)
    return MOD_ERROR_VAL;

  import_array();
  return MOD_SUCCESS_VAL(mod);
}

static PyObject *sstpert_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  double factor = 0.0;
  PyArrayObject *dt;
  PyArrayObject *fieldclim;

  // Note the argument descriptors "s#d":
  if (!PyArg_ParseTuple(args, "dOO", &factor, &dt, &fieldclim )) return NULL;

  // Cast self to void to avoid unused paramter errors
  (void) self;

  // Setup output array object and dimensions
  PyArrayObject *npy_array_out = NULL;
  npy_intp dims_out[2];

  // Get dimensions of input fieldclim array
  npy_intp *dims_clim = PyArray_DIMS(fieldclim);
  int64_t rows = (int64_t) dims_clim[0];
  int64_t cols = (int64_t) dims_clim[1];
  int64_t months = (int64_t) dims_clim[2];
  double *field_ptr = (double *) PyArray_DATA(fieldclim);

  if (months != 12) {
    PyErr_SetString(PyExc_ValueError, 
                     "Climatology must have a final dimension of 12");
    return NULL;
  } 

  // Attach to the dt array
  npy_intp *dims_dt = PyArray_DIMS(dt);
  int64_t len_dt = dims_dt[0];
  int64_t *dt_ptr = (int64_t *) PyArray_DATA(dt);
  if (len_dt != 8) {
    PyErr_SetString(PyExc_ValueError, "Date array must have 8 elements");
    return NULL;
  } 

  // Allocate space for return value
  int64_t len_comp = rows*cols;
  double *dataout = 
    (double*)calloc((size_t)(len_comp), sizeof(double));
  if (dataout == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for sstpert");
    return NULL;
  } 

  sstpert(&factor,
          dt_ptr,
          &rows,
          &cols,
          field_ptr,
          dataout);

  // Now form a numpy array object to return to python
  dims_out[0] = rows;
  dims_out[1] = cols;
  npy_array_out=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims_out,
                                                            NPY_DOUBLE,
                                                            dataout);
  if (npy_array_out == NULL) {
    free(dataout);
    PyErr_SetString(PyExc_ValueError, "Failed to make numpy array");
    return NULL;
  }

  // Give python/numpy ownership of the memory storing the return array
  #if NPY_API_VERSION >= NPY_1_7_API_VERSION
  PyArray_ENABLEFLAGS(npy_array_out, NPY_ARRAY_OWNDATA);
  #else
  npy_array_out->flags = npy_array_out->flags | NPY_OWNDATA;
  #endif

  return (PyObject *)npy_array_out;
}

static PyObject *sstpertseed_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  PyArrayObject *dt;

  if (!PyArg_ParseTuple(args, "O", &dt )) return NULL;

  // Cast self to void to avoid unused parameter errors
  (void) self;

  // Attach to the dt array
  npy_intp *dims_dt = PyArray_DIMS(dt);
  int64_t len_dt = dims_dt[0];
  int64_t *dt_ptr = (int64_t *) PyArray_DATA(dt);
  if (len_dt != 8) {
    PyErr_SetString(PyExc_ValueError, "Date array must have 8 elements");
    return NULL;
  }

  int64_t seed;

  sstpertseed(dt_ptr, &seed);

  PyObject *seedval = NULL;
  seedval = PyInt_FromLong((long) seed);
  return seedval;
}
